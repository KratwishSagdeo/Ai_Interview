from dotenv import load_dotenv
load_dotenv()

from configs.logger import setup_logging
setup_logging(level="INFO")

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from collections import defaultdict
import shutil
import os
import uuid
import time
import asyncio
import json

from interview_engine.interview_manager import InterviewManager
from pipelines.evaluation_pipeline import SpeechEvaluationPipeline
from configs.job_roles import list_roles
from asr.realtime_buffer import RealtimeAudioBuffer

app = FastAPI()

speech_pipeline = SpeechEvaluationPipeline()
sessions = {}

# ✅ Track session creation time for auto-cleanup
session_created_at = {}
SESSION_TTL_SECONDS = 3600      # Sessions expire after 1 hour


# ====================================================
# ✅ P1: API KEY PROTECTION
# ====================================================
# Add this to your .env file:
#   INTERVIEW_API_KEY=pick-any-long-random-string
#
# Your friend's frontend must send this header with every request:
#   X-API-Key: <your key>
#
# /job-roles and /docs are left public intentionally.
# ====================================================

API_KEY = os.getenv("INTERVIEW_API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(key: str = Depends(api_key_header)):
    if not API_KEY:
        return          # If no key set in .env, skip check (local dev mode)
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key. Send X-API-Key header.")


# ====================================================
# ✅ P1: RATE LIMITING
# ====================================================
# Limits per IP:
#   /upload-resume  → 5 requests per minute  (starting a new interview)
#   /submit-answer  → 30 requests per minute (answering questions)
#   /ws/*           → 10 connections per minute
# ====================================================

# Stores: { ip: { endpoint: [timestamp, ...] } }
rate_limit_store: dict = defaultdict(lambda: defaultdict(list))

RATE_LIMITS = {
    "upload_resume":  (5,  60),     # 5 per 60 seconds
    "submit_answer":  (30, 60),     # 30 per 60 seconds
    "websocket":      (10, 60),     # 10 per 60 seconds
}

def check_rate_limit(request: Request, endpoint: str):
    ip = request.client.host
    max_calls, window = RATE_LIMITS[endpoint]
    now = time.time()

    # Keep only timestamps within the current window
    calls = rate_limit_store[ip][endpoint]
    rate_limit_store[ip][endpoint] = [t for t in calls if now - t < window]

    if len(rate_limit_store[ip][endpoint]) >= max_calls:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {max_calls} requests per {window}s for this endpoint."
        )

    rate_limit_store[ip][endpoint].append(now)


# ----------------------------------------------------
# ✅ Session cleanup — runs silently on every request
# ----------------------------------------------------

def cleanup_expired_sessions():
    now = time.time()
    expired = [sid for sid, t in session_created_at.items() if now - t > SESSION_TTL_SECONDS]
    for sid in expired:
        sessions.pop(sid, None)
        session_created_at.pop(sid, None)
        print(f"🧹 Expired session removed: {sid}")


# ----------------------------------------------------
# Job roles
# ----------------------------------------------------

@app.get("/job-roles")
def get_job_roles():
    return {"roles": list_roles()}


# ----------------------------------------------------
# Upload resume + start interview
# ----------------------------------------------------

@app.post("/upload-resume")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    job_role: str = Form(default="software_engineer"),
    _: str = Depends(verify_api_key)
):
    print("Incoming job_role from request:", job_role)
    
    if not job_role or len(job_role.strip()) < 3:
        raise HTTPException(status_code=400, detail="Invalid job role")

    check_rate_limit(request, "upload_resume")
    cleanup_expired_sessions()

    try:
        path = f"temp_{file.filename}"
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        session_id = str(uuid.uuid4())
        manager = InterviewManager()
        question = await asyncio.to_thread(manager.start_interview, path, job_role)

        sessions[session_id] = {
            "session_id": session_id,
            "manager": manager,
            "job_role": manager.job_role.get("title", job_role),
            "skills": manager.skills
        }
        session_created_at[session_id] = time.time()

        return {
            "session_id": session_id,
            "question": question,
            "job_role": sessions[session_id]["job_role"]
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        # ✅ Always clean up resume temp file
        if "path" in locals() and os.path.exists(path):
            os.remove(path)


# ----------------------------------------------------
# Submit answer (REST — keep for testing)
# ----------------------------------------------------

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

        session = sessions[session_id]
        manager = session["manager"]

        # ✅ Block further answers if interview already finished
        if manager.is_finished:
            return {
                "interview_complete": True,
                "message": "This interview has already ended. Call /get-report to retrieve results."
            }

        if not file.filename.endswith((".wav", ".mp3", ".flac", ".ogg")):
            return {"error": "Only audio files (.wav, .mp3, .flac, .ogg) are allowed"}

        path = f"temp_{file.filename}"
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print("=" * 50)
        print("🎤 STAGE 1: Speech-to-Text (Groq Cloud)...")
        stt_start = time.time()
        text, timestamps = await asyncio.to_thread(speech_pipeline.transcribe, path)
        print(f"⏱  STT Time: {time.time() - stt_start:.2f}s")

        transcript = text if text else ""
        if not transcript.strip():
            return {
                "transcript": "",
                "fluency_score": 0,
                "next_question": "Could you please repeat your answer?"
            }

        print("🚀 STAGE 2: Running Groq + Analysis in PARALLEL...")
        analysis_start = time.time()

        analysis_task = asyncio.to_thread(speech_pipeline.analyze, path, text, timestamps)

        # Run analysis first to get fluency metrics for weak area detection
        analysis_result = await analysis_task

        # ✅ Pass fluency metrics into process_answer for weak area detection
        result = await asyncio.to_thread(
            manager.process_answer, transcript, analysis_result
        )

        print(f"⏱  Analysis Time: {time.time() - analysis_start:.2f}s")
        print(f"✅ TOTAL Response Time: {time.time() - total_start:.2f}s")
        print("=" * 50)

        response = {
            "transcript": transcript,
            "fluency_score": analysis_result.get("fluency_score", 0),
            "speech_rate": analysis_result.get("speech_rate", 0),
            "pause_count": analysis_result.get("pause_count", 0),
            "filler_count": analysis_result.get("filler_count", 0),
            "grammar_errors": analysis_result.get("grammar_errors", 0),
            "lexical_diversity": analysis_result.get("lexical_diversity", 0),
            "job_role": manager.job_role.get("title", "") if manager.job_role else ""
        }

        # ✅ Wire in end logic
        if result["type"] == "end":
            response["interview_complete"] = True
            response["next_question"] = result["content"]
        else:
            response["interview_complete"] = False
            response["next_question"] = result["content"]

        return response

    except Exception as e:
        print(f"❌ Server error: {e}")
        return {"error": str(e)}

    finally:
        # ✅ Always clean up audio temp file
        if path and os.path.exists(path):
            os.remove(path)


# ----------------------------------------------------
# ✅ NEW: Final report endpoint
# ----------------------------------------------------

@app.get("/get-report/{session_id}")
async def get_report(session_id: str, _: str = Depends(verify_api_key)):
    """
    Call this after interview_complete=True to get the full report.
    Can also be called mid-interview to get a partial report.
    """

    if session_id not in sessions:
        return {"error": "Invalid session_id or session has expired"}

    session = sessions[session_id]
    manager = session["manager"]

    try:
        report = manager.generate_report()
        return report

    except Exception as e:
        print(f"❌ Report generation error: {e}")
        return {"error": str(e)}


# ----------------------------------------------------
# ✅ NEW: Manual end interview endpoint
# ----------------------------------------------------

@app.post("/end-interview/{session_id}")
async def end_interview(session_id: str, _: str = Depends(verify_api_key)):
    """
    Lets the frontend manually end the interview early.
    Returns the final report immediately.
    """

    if session_id not in sessions:
        return {"error": "Invalid session_id"}

    session = sessions[session_id]
    manager = session["manager"]
    manager.is_finished = True
    manager.end_reason = "manual"

    try:
        report = manager.generate_report()
        return {
            "message": "Interview ended manually.",
            "report": report
        }
    except Exception as e:
        return {"error": str(e)}


# ====================================================
# WebSocket — real-time streaming
# ====================================================
#
# FRONTEND INTEGRATION GUIDE:
#
# 1. POST /upload-resume → get session_id + first question
# 2. Connect: ws://yourserver/ws/{session_id}
# 3. Send raw audio chunks as binary (16kHz mono 16-bit PCM) every ~250ms
# 4. Server auto-detects 1.5s silence and processes automatically
#    OR send: { "event": "end_of_speech" } to trigger manually
# 5. Server sends two messages back:
#    { "event": "transcript", "transcript": "..." }         ← immediate
#    { "event": "result", "next_question": "...", ... }     ← after LLM
#    { "event": "interview_complete", "report": {...} }     ← when done
# 6. On "interview_complete", show the report to the user
# 7. To end early: { "event": "end_interview" }
#
# ====================================================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):

    await websocket.accept()
    print(f"🔌 WebSocket connected: {session_id}")

    # ✅ Rate limit WebSocket connections by IP
    try:
        check_rate_limit(websocket, "websocket")
    except HTTPException as e:
        await websocket.send_text(json.dumps({"event": "error", "message": e.detail}))
        await websocket.close()
        return

    if session_id not in sessions:
        await websocket.send_text(json.dumps({
            "event": "error",
            "message": "Invalid session_id. Call /upload-resume first."
        }))
        await websocket.close()
        return

    session = sessions[session_id]
    manager = session["manager"]
    buffer = RealtimeAudioBuffer(sample_rate=16000)

    async def process_buffered_audio():

        audio_path = f"temp_ws_{session_id}.wav"

        try:
            buffer.save_to_wav(audio_path)
            total_start = time.time()

            # STT
            text, timestamps = await asyncio.to_thread(
                speech_pipeline.transcribe, audio_path
            )
            transcript = text if text else ""

            if not transcript.strip():
                await websocket.send_text(json.dumps({
                    "event": "result",
                    "transcript": "",
                    "next_question": "Could you please repeat your answer?",
                    "interview_complete": False,
                    "fluency_score": 0,
                    "speech_rate": 0,
                    "pause_count": 0,
                    "filler_count": 0,
                    "grammar_errors": 0,
                    "lexical_diversity": 0
                }))
                buffer.clear()
                return

            # Send transcript immediately
            await websocket.send_text(json.dumps({
                "event": "transcript",
                "transcript": transcript
            }))

            # Run analysis
            analysis_result = await asyncio.to_thread(
                speech_pipeline.analyze, audio_path, text, timestamps
            )

            # Process answer with fluency metrics
            result = await asyncio.to_thread(
                manager.process_answer, transcript, analysis_result
            )

            print(f"✅ WebSocket Response Time: {time.time() - total_start:.2f}s")

            # ✅ Handle end vs next question
            if result["type"] == "end":
                report = manager.generate_report()
                await websocket.send_text(json.dumps({
                    "event": "interview_complete",
                    "message": result["content"],
                    "report": report
                }))
            else:
                await websocket.send_text(json.dumps({
                    "event": "result",
                    "transcript": transcript,
                    "next_question": result["content"],
                    "interview_complete": False,
                    "fluency_score": analysis_result.get("fluency_score", 0),
                    "speech_rate": analysis_result.get("speech_rate", 0),
                    "pause_count": analysis_result.get("pause_count", 0),
                    "filler_count": analysis_result.get("filler_count", 0),
                    "grammar_errors": analysis_result.get("grammar_errors", 0),
                    "lexical_diversity": analysis_result.get("lexical_diversity", 0)
                }))

        except Exception as e:
            print(f"❌ WebSocket processing error: {e}")
            await websocket.send_text(json.dumps({
                "event": "error",
                "message": str(e)
            }))

        finally:
            buffer.clear()
            if os.path.exists(audio_path):
                os.remove(audio_path)

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"]:
                buffer.add_chunk(message["bytes"])
                if buffer.is_silent_long_enough():
                    print("🔇 Silence detected — auto-processing...")
                    await process_buffered_audio()

            elif "text" in message and message["text"]:
                try:
                    event = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue

                if event.get("event") == "end_of_speech":
                    print("🎤 End of speech signal received")
                    await process_buffered_audio()

                elif event.get("event") == "end_interview":
                    manager.is_finished = True
                    manager.end_reason = "manual"
                    report = manager.generate_report()
                    await websocket.send_text(json.dumps({
                        "event": "interview_complete",
                        "message": "Interview ended manually.",
                        "report": report
                    }))
                    break

    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected: {session_id}")

    finally:
        buffer.clear()
        print(f"🧹 Cleaned up: {session_id}")