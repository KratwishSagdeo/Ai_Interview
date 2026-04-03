from dotenv import load_dotenv
load_dotenv()

from configs.logger import setup_logging
setup_logging(level="INFO")

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from collections import defaultdict
import shutil
import os
import uuid
import time
import asyncio
import json
import logging
import datetime

from services.pdf_generator import PDFReportGenerator
from fastapi.responses import FileResponse
from fastapi import BackgroundTasks
import tempfile

from interview_engine.interview_manager import InterviewManager
from pipelines.evaluation_pipeline import SpeechEvaluationPipeline
from configs.job_roles import list_roles
from asr.realtime_buffer import RealtimeAudioBuffer
from services.semantic_validator import is_relevant_answer

logger = logging.getLogger("server")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


speech_pipeline = SpeechEvaluationPipeline()
sessions = {}
session_created_at = {}
SESSION_TTL_SECONDS = 3600



# ----------------------------------------------------
# Auth
# ----------------------------------------------------

API_KEY = os.getenv("INTERVIEW_API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(key: str = Depends(api_key_header)):
    if not API_KEY:
        return
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

# ----------------------------------------------------
# Rate limiting
# ----------------------------------------------------

rate_limit_store: dict = defaultdict(lambda: defaultdict(list))
RATE_LIMITS = {
    "upload_resume": (5,  60),
    "submit_answer": (30, 60),
    "websocket":     (10, 60),
}

def check_rate_limit(request: Request, endpoint: str):
    ip = request.client.host
    max_calls, window = RATE_LIMITS[endpoint]
    now = time.time()
    calls = rate_limit_store[ip][endpoint]
    rate_limit_store[ip][endpoint] = [t for t in calls if now - t < window]
    if len(rate_limit_store[ip][endpoint]) >= max_calls:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Max {max_calls} per {window}s.")
    rate_limit_store[ip][endpoint].append(now)

# ----------------------------------------------------
# Session cleanup
# ----------------------------------------------------

def cleanup_expired_sessions():
    now = time.time()
    expired = [sid for sid, t in session_created_at.items() if now - t > SESSION_TTL_SECONDS]
    for sid in expired:
        sessions.pop(sid, None)
        session_created_at.pop(sid, None)
        logger.info(f"Expired session removed: {sid}")

# ----------------------------------------------------
# Helper — build response dict from result + analysis
# ----------------------------------------------------

def build_answer_response(transcript, result, analysis_result, manager):
    """Shared response builder for REST and WebSocket."""

    evaluation = result.get("evaluation", {})

    base = {
        "transcript":         transcript,
        "next_question":      result["content"],
        "interview_complete": result["type"] == "end",

        # Fluency
        "fluency_score":      analysis_result.get("fluency_score", 0),
        "speech_rate":        analysis_result.get("speech_rate", 0),
        "pause_count":        analysis_result.get("pause_count", 0),
        "filler_count":       analysis_result.get("filler_count", 0),
        "grammar_errors":     analysis_result.get("grammar_errors", 0),
        "lexical_diversity":  analysis_result.get("lexical_diversity", 0),

        # ✅ Content evaluation
        "content_score":      evaluation.get("final_score", 0),
        "correctness":        evaluation.get("correctness", 0),
        "depth":              evaluation.get("depth", 0),
        "clarity":            evaluation.get("clarity", 0),
        "consistency":        evaluation.get("consistency", 0),
        "confidence_level":   evaluation.get("confidence", 0.3),
        "reasoning":          evaluation.get("feedback", ""),

        "job_role":           manager.job_role.get("title", "") if manager.job_role else "",
        "average_score":      round(manager.average_score, 3),
        "questions_asked":    len(manager.questions_asked),
    }

    return base


# ----------------------------------------------------
# Endpoints
# ----------------------------------------------------

@app.get("/job-roles")
def get_job_roles():
    return {"roles": list_roles()}


@app.post("/upload-resume")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    job_role: str = Form(default="software_engineer"),
    experience_level: str = Form(default="beginner"),
    interview_type: str = Form(default="full"),
    _: str = Depends(verify_api_key)
):
    if not job_role or len(job_role.strip()) < 3:
        raise HTTPException(status_code=400, detail="Invalid job role")

    logger.info(f"Form received: job_role={job_role} level={experience_level} type={interview_type}")

    check_rate_limit(request, "upload_resume")
    cleanup_expired_sessions()

    path = None
    try:
        path = f"temp_{file.filename}"
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        session_id = str(uuid.uuid4())
        manager = InterviewManager()
        question = await asyncio.to_thread(manager.start_interview, path, job_role, experience_level, interview_type)

        sessions[session_id] = {
            "session_id": session_id,
            "manager": manager,
            "job_role": manager.job_role.get("title", job_role),
            "skills": manager.skills
        }
        session_created_at[session_id] = time.time()

        return {
            "session_id": session_id,
            "question":   question,
            "job_role":   sessions[session_id]["job_role"]
        }

    except Exception as e:
        logger.error(f"upload_resume error: {e}")
        return {"error": str(e)}

    finally:
        if path and os.path.exists(path):
            os.remove(path)


@app.post("/submit-answer")
async def submit_answer(
    request: Request,
    session_id: str = Form(...),
    file: UploadFile = File(...),
    _: str = Depends(verify_api_key)
):
    check_rate_limit(request, "submit_answer")
    cleanup_expired_sessions()

    path = None
    try:
        total_start = time.time()

        if session_id not in sessions:
            return {"error": "Invalid session_id"}

        manager = sessions[session_id]["manager"]

        if manager.is_finished:
            return {
                "interview_complete": True,
                "message": "Interview already ended. Call /get-report to retrieve results."
            }

        if not file.filename.endswith((".wav", ".mp3", ".flac", ".ogg")):
            return {"error": "Only audio files (.wav, .mp3, .flac, .ogg) are allowed"}

        path = f"temp_{file.filename}"
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Stage 1: STT
        text, timestamps = await asyncio.to_thread(speech_pipeline.transcribe, path)
        transcript = text if text else ""

        if not transcript.strip():
            return {"transcript": "", "fluency_score": 0, "next_question": "Could you please repeat your answer?"}
            
        # SEMANTIC VALIDATION
        current_question = manager.questions_asked[manager.current_question_index] if manager.current_question_index < len(manager.questions_asked) else "Tell me about yourself."
        
        validation_data = await asyncio.to_thread(is_relevant_answer, current_question, transcript)
        verdict = validation_data.get("verdict", "RELEVANT")
        
        print("Heuristic + LLM validation result:", verdict)
        
        if verdict == "IRRELEVANT":
            print("🚫 TERMINATING INTERVIEW DUE TO INVALID ANSWER")
            manager.is_finished = True
            manager.end_reason = "irrelevant_answer"
            report = manager.generate_report()
            
            return {
                "type": "interview_terminated",
                "message": "This is your final warning. The interview has been terminated due to inappropriate or irrelevant response.",
                "reason": "irrelevant_answer",
                "interview_complete": True,
                "report": report
            }
        
        elif verdict == "PARTIALLY_RELEVANT":
            print("⚠️ PARTIALLY RELEVANT ANSWER DETECTED")
            # We allow it through, but it will be evaluated poorly by the pipeline.

        # Stage 2: Fluency analysis + answer evaluation in parallel
        analysis_task = asyncio.to_thread(speech_pipeline.analyze, path, text, timestamps)
        analysis_result = await analysis_task

        try:
            result = await asyncio.to_thread(manager.process_answer, transcript, analysis_result)
        except Exception as e:
            logger.error(f"Evaluation step failed: {e}")
            result = {
                "type": "continue",
                "content": "I apologize, there was an error processing your answer. Let's move to the next question.",
                "evaluation": {"final_score": 0.0, "confidence_level": "low"}
            }

        logger.info(f"Total response time: {time.time() - total_start:.2f}s")

        return build_answer_response(transcript, result, analysis_result, manager)

    except Exception as e:
        logger.error(f"submit_answer error: {e}")
        return {"error": str(e)}

    finally:
        if path and os.path.exists(path):
            os.remove(path)


@app.get("/get-report/{session_id}")
async def get_report(session_id: str, _: str = Depends(verify_api_key)):
    if session_id not in sessions:
        return {"error": "Invalid session_id or session has expired"}
    try:
        return sessions[session_id]["manager"].generate_report()
    except Exception as e:
        logger.error(f"get_report error: {e}")
        return {"error": str(e)}


@app.post("/generate-report/{session_id}")
async def generate_report_endpoint(session_id: str):
    if session_id not in sessions:
        return {"error": "Invalid session_id or session has expired"}
    manager = sessions[session_id]["manager"]
    manager.is_finished = True
    manager.end_reason = "manual"
    try:
        report = manager.generate_report()
        return report
    except Exception as e:
        logger.error(f"generate-report error: {e}")
        return {"error": str(e)}

@app.post("/generate-pdf/{session_id}")
async def generate_pdf_endpoint(session_id: str, background_tasks: BackgroundTasks, _: str = Depends(verify_api_key)):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Invalid session_id or session has expired")
    
    manager = sessions[session_id]["manager"]
    report = manager.generate_report()
    
    job_role = report.get("session_summary", {}).get("job_role", "candidate").replace(" ", "_").lower()
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    filename = f"interview_report_{job_role}_{date_str}.pdf"
    
    # Create temp file
    fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    
    # Generate PDF
    generator = PDFReportGenerator()
    generator.generate(report, temp_path)
    
    # Delete after sending
    background_tasks.add_task(os.remove, temp_path)
    
    return FileResponse(
        path=temp_path,
        filename=filename,
        media_type="application/pdf"
    )


@app.post("/end-interview/{session_id}")
async def end_interview(session_id: str, _: str = Depends(verify_api_key)):
    if session_id not in sessions:
        return {"error": "Invalid session_id"}
    manager = sessions[session_id]["manager"]
    manager.is_finished = True
    manager.end_reason = "manual"
    try:
        return {"message": "Interview ended manually.", "report": manager.generate_report()}
    except Exception as e:
        return {"error": str(e)}


# ----------------------------------------------------
# WebSocket
# ✅ Accepts api_key as query param (browsers can't send headers over WS)
# ----------------------------------------------------

@app.websocket("/ws/audio/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str
):
    api_key = websocket.query_params.get("api_key")

    print("API key received")

    # Auth
    if API_KEY and api_key != API_KEY:
        try:
            await websocket.close(code=1008)
        except:
            pass
        return

    await websocket.accept()
    print(f"✅ CONNECTED: {session_id}")
    print("✅ Ready to receive messages (no handshake required)")

    # 🔥 DEBUG (VERY IMPORTANT)
    print("🔍 Active sessions:", list(sessions.keys()))
    print("🔍 Incoming session:", session_id)

    if session_id not in sessions:
        await websocket.send_text(json.dumps({
            "event": "error",
            "message": "Invalid session_id."
        }))
        print("❌ Invalid session_id — keeping socket open for debug")
        return  # 🔥 DO NOT CLOSE (prevents crash)

    manager = sessions[session_id]["manager"]
    buffer = RealtimeAudioBuffer(sample_rate=16000)
    logger.info(f"WebSocket connected: {session_id}")

    # Send first question
    initial_question = (
        manager.questions_asked[0]
        if manager.questions_asked
        else "Tell me about yourself."
    )

    await websocket.send_text(json.dumps({
        "type": "question",
        "text": initial_question
    }))

    # --------------------------------------------------
    # AUDIO PROCESSING TASK
    # --------------------------------------------------
    async def process_audio_task(audio_path: str):
        try:
            text, timestamps = await asyncio.to_thread(
                speech_pipeline.transcribe, audio_path
            )
            transcript = text if text else ""

            if not transcript.strip():
                await websocket.send_text(json.dumps({
                    "type": "result",
                    "transcript": "",
                    "next_question": "Could you please repeat your answer?",
                    "interview_complete": False
                }))
                return

            print(f"📝 Transcript: {transcript}")

            await websocket.send_text(json.dumps({
                "type": "transcript",
                "text": transcript
            }))

            # Validation
            current_question = (
                manager.questions_asked[manager.current_question_index]
                if manager.current_question_index < len(manager.questions_asked)
                else "Tell me about yourself."
            )

            validation_data = await asyncio.to_thread(
                is_relevant_answer,
                current_question,
                transcript
            )

            verdict = validation_data.get("verdict", "RELEVANT")
            print("Validation:", verdict)

            if verdict == "IRRELEVANT":
                manager.is_finished = True
                manager.end_reason = "irrelevant_answer"

                await websocket.send_text(json.dumps({
                    "type": "interview_terminated",
                    "message": "Interview terminated due to irrelevant answer."
                }))

                report = manager.generate_report()

                await websocket.send_text(json.dumps({
                    "type": "final_report",
                    "data": report
                }))
                return

            analysis_result = await asyncio.to_thread(
                speech_pipeline.analyze,
                audio_path,
                text,
                timestamps
            )

            try:
                result = await asyncio.to_thread(
                    manager.process_answer,
                    transcript,
                    analysis_result
                )
            except Exception as e:
                logger.error(f"Evaluation failed: {e}")
                result = {
                    "type": "continue",
                    "content": "Error processing answer. Moving on.",
                    "evaluation": {"final_score": 0.0}
                }

            if result["type"] == "end":
                report = manager.generate_report()
                await websocket.send_text(json.dumps({
                    "type": "interview_complete",
                    "message": result["content"],
                    "report": report
                }))
            else:
                payload = build_answer_response(
                    transcript, result, analysis_result, manager
                )
                await websocket.send_text(json.dumps({
                "type": "transcript",
                "text": transcript
                }))
                await websocket.send_text(json.dumps({
    "type": "evaluation",
    "feedback": payload.get("reasoning", ""),
    "content_score": payload.get("content_score", 0),
    "fluency_score": payload.get("fluency_score", 0),
    "avg_score": payload.get("average_score", 0)
                }))
                await websocket.send_text(json.dumps({
    "type": "question",
    "text": payload.get("next_question", "Let's continue.")
}))


        except Exception as e:
            logger.error(f"Processing error: {e}")
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

    # --------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------
    try:
        while True:
            try:
                message = await websocket.receive()
            except WebSocketDisconnect:
                print("❌ Client disconnected")
                break
            except Exception as e:
                print("⚠️ Receive error:", e)
                break

            print("📩 RAW MESSAGE:", message)

            if "bytes" in message and message["bytes"]:
                raw = message["bytes"]
                buffer.add_chunk(raw)

                if buffer.is_silent_long_enough():
                    if buffer.chunks:
                        audio_path = f"temp_ws_{uuid.uuid4().hex[:6]}.wav"
                        buffer.save_to_wav(audio_path)
                        asyncio.create_task(process_audio_task(audio_path))
                    buffer.clear()

            elif "text" in message and message["text"]:
                try:
                    event = json.loads(message["text"])
                except:
                    continue

                if event.get("type") == "end_of_speech":
                    if buffer.chunks:
                        audio_path = f"temp_ws_{uuid.uuid4().hex[:6]}.wav"
                        buffer.save_to_wav(audio_path)
                        asyncio.create_task(process_audio_task(audio_path))
                    buffer.clear()

                elif event.get("type") == "end_interview":
                    manager.is_finished = True
                    manager.end_reason = "manual"

                    report = manager.generate_report()

                    await websocket.send_text(json.dumps({
                        "type": "interview_complete",
                        "message": "Interview ended.",
                        "report": report
                    }))
                    break

    finally:
        buffer.clear()
        logger.info(f"🧹 Cleaned up session: {session_id}")