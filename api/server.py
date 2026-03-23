# ----------------------------------------------------
# Load environment variables
# ----------------------------------------------------

from dotenv import load_dotenv
load_dotenv()


# ----------------------------------------------------
# Import required libraries
# ----------------------------------------------------

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
import shutil
import os
import uuid
import time
import asyncio
import json


# ----------------------------------------------------
# Import AI modules
# ----------------------------------------------------

from interview_engine.interview_manager import InterviewManager
from pipelines.evaluation_pipeline import SpeechEvaluationPipeline
from configs.job_roles import list_roles
from asr.realtime_buffer import RealtimeAudioBuffer


# ----------------------------------------------------
# Initialize FastAPI app
# ----------------------------------------------------

app = FastAPI()


# ----------------------------------------------------
# Initialize global systems
# ----------------------------------------------------

speech_pipeline = SpeechEvaluationPipeline()
sessions = {}


# ----------------------------------------------------
# Get available job roles (for frontend dropdown)
# ----------------------------------------------------

@app.get("/job-roles")
def get_job_roles():
    return {"roles": list_roles()}


# ----------------------------------------------------
# Upload Resume Endpoint (START INTERVIEW)
# ----------------------------------------------------

@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    job_role: str = Form(default="software_engineer")
):
    try:
        path = f"temp_{file.filename}"
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        session_id = str(uuid.uuid4())
        manager = InterviewManager()
        question = await asyncio.to_thread(manager.start_interview, path, job_role)
        sessions[session_id] = manager

        return {
            "session_id": session_id,
            "question": question,
            "job_role": manager.job_role.get("title", job_role)
        }

    except Exception as e:
        return {"error": str(e)}


# ----------------------------------------------------
# Submit Audio Answer Endpoint (REST — keep for testing)
# ----------------------------------------------------

@app.post("/submit-answer")
async def submit_answer(
    session_id: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        total_start = time.time()

        if session_id not in sessions:
            return {"error": "Invalid session_id"}

        manager = sessions[session_id]

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
            return {"transcript": "", "fluency_score": 0, "next_question": "Could you please repeat your answer?"}

        print("🚀 STAGE 2: Running Groq + Analysis in PARALLEL...")
        analysis_start = time.time()

        groq_task = asyncio.to_thread(manager.process_answer, transcript)
        analysis_task = asyncio.to_thread(speech_pipeline.analyze, path, text, timestamps)
        next_question, analysis_result = await asyncio.gather(groq_task, analysis_task)

        print(f"⏱  Analysis Time: {time.time() - analysis_start:.2f}s")
        print(f"✅ TOTAL Response Time: {time.time() - total_start:.2f}s")
        print("=" * 50)

        return {
            "transcript": transcript,
            "fluency_score": analysis_result.get("fluency_score", 0),
            "speech_rate": analysis_result.get("speech_rate", 0),
            "pause_count": analysis_result.get("pause_count", 0),
            "filler_count": analysis_result.get("filler_count", 0),
            "grammar_errors": analysis_result.get("grammar_errors", 0),
            "lexical_diversity": analysis_result.get("lexical_diversity", 0),
            "next_question": next_question,
            "job_role": manager.job_role.get("title", "") if manager.job_role else ""
        }

    except Exception as e:
        print(f"❌ Server error: {e}")
        return {"error": str(e)}


# ====================================================
# ✅ NEW: WebSocket Endpoint for Real-Time Streaming
# ====================================================
#
# HOW YOUR FRIEND'S FRONTEND SHOULD USE THIS:
#
# STEP 1 — Call POST /upload-resume to get session_id + first question
#
# STEP 2 — Connect WebSocket:
#   ws = new WebSocket("ws://yourserver/ws/{session_id}")
#
# STEP 3 — Send raw audio chunks as binary (ArrayBuffer) while speaking:
#   ws.send(audioChunkArrayBuffer)
#   (chunks should be 16kHz, mono, 16-bit PCM — send every 250ms)
#
# STEP 4 — Either:
#   a) Let server auto-detect silence (1.5s) and trigger processing, OR
#   b) Send this JSON when candidate finishes speaking:
#      ws.send(JSON.stringify({ "event": "end_of_speech" }))
#
# STEP 5 — Server sends back two messages:
#   First (immediate):  { "event": "transcript", "transcript": "..." }
#   Then (after LLM):   { "event": "result", "next_question": "...", ...scores }
#
# STEP 6 — Show next_question, start recording next answer, repeat from STEP 3
#
# STEP 7 — To end interview:
#   ws.send(JSON.stringify({ "event": "end_interview" }))
#
# ====================================================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):

    await websocket.accept()
    print(f"🔌 WebSocket connected: {session_id}")

    # Validate session exists
    if session_id not in sessions:
        await websocket.send_text(json.dumps({
            "event": "error",
            "message": "Invalid session_id. Call /upload-resume first."
        }))
        await websocket.close()
        return

    manager = sessions[session_id]
    buffer = RealtimeAudioBuffer(sample_rate=16000)

    async def process_buffered_audio():
        """Save buffered audio to file and run full STT + LLM + analysis pipeline."""

        audio_path = f"temp_ws_{session_id}.wav"

        try:
            buffer.save_to_wav(audio_path)
            total_start = time.time()

            # Stage 1: STT
            text, timestamps = await asyncio.to_thread(
                speech_pipeline.transcribe, audio_path
            )
            transcript = text if text else ""

            if not transcript.strip():
                await websocket.send_text(json.dumps({
                    "event": "result",
                    "transcript": "",
                    "next_question": "Could you please repeat your answer?",
                    "fluency_score": 0,
                    "speech_rate": 0,
                    "pause_count": 0,
                    "filler_count": 0,
                    "grammar_errors": 0,
                    "lexical_diversity": 0
                }))
                buffer.clear()
                return

            # Send transcript immediately (frontend can show it while LLM runs)
            await websocket.send_text(json.dumps({
                "event": "transcript",
                "transcript": transcript
            }))

            # Stage 2: LLM + analysis in parallel
            groq_task = asyncio.to_thread(manager.process_answer, transcript)
            analysis_task = asyncio.to_thread(
                speech_pipeline.analyze, audio_path, text, timestamps
            )
            next_question, analysis_result = await asyncio.gather(
                groq_task, analysis_task
            )

            print(f"✅ WebSocket Response Time: {time.time() - total_start:.2f}s")

            # Send full result
            await websocket.send_text(json.dumps({
                "event": "result",
                "transcript": transcript,
                "next_question": next_question,
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

            # Binary = raw audio chunk from microphone
            if "bytes" in message and message["bytes"]:
                buffer.add_chunk(message["bytes"])

                # Auto-trigger if silence detected
                if buffer.is_silent_long_enough():
                    print("🔇 Silence detected — auto-processing...")
                    await process_buffered_audio()

            # Text = control event from frontend
            elif "text" in message and message["text"]:
                try:
                    event = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue

                if event.get("event") == "end_of_speech":
                    print("🎤 End of speech signal received")
                    await process_buffered_audio()

                elif event.get("event") == "end_interview":
                    await websocket.send_text(json.dumps({
                        "event": "interview_ended",
                        "message": "Interview session closed."
                    }))
                    break

    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected: {session_id}")

    finally:
        buffer.clear()
        print(f"🧹 Cleaned up: {session_id}")