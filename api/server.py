# ----------------------------------------------------
# Load environment variables
# ----------------------------------------------------

from dotenv import load_dotenv
load_dotenv()


# ----------------------------------------------------
# Import required libraries
# ----------------------------------------------------

from fastapi import FastAPI, UploadFile, File, Form
import shutil
import os
import uuid
import time
import asyncio


# ----------------------------------------------------
# Import AI modules
# ----------------------------------------------------

from interview_engine.interview_manager import InterviewManager
from pipelines.evaluation_pipeline import SpeechEvaluationPipeline

# ✅ NEW: Import job roles config
from configs.job_roles import list_roles


# ----------------------------------------------------
# Initialize FastAPI app
# ----------------------------------------------------

app = FastAPI()


# ----------------------------------------------------
# Initialize global systems
# ----------------------------------------------------

speech_pipeline = SpeechEvaluationPipeline()

# Dictionary to store multiple interview sessions
sessions = {}


# ----------------------------------------------------
# ✅ NEW: Get available job roles (for frontend dropdown)
# ----------------------------------------------------

@app.get("/job-roles")
def get_job_roles():
    """Returns list of available job roles for the frontend dropdown."""
    return {"roles": list_roles()}


# ----------------------------------------------------
# Upload Resume Endpoint (START INTERVIEW)
# ✅ Now accepts job_role field
# ----------------------------------------------------

@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    job_role: str = Form(default="software_engineer")   # ✅ NEW field
):

    try:

        path = f"temp_{file.filename}"

        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        session_id = str(uuid.uuid4())

        manager = InterviewManager()

        # ✅ Pass job_role into start_interview
        question = await asyncio.to_thread(manager.start_interview, path, job_role)

        sessions[session_id] = manager

        return {
            "session_id": session_id,
            "question": question,
            "job_role": manager.job_role.get("title", job_role)   # ✅ Return role title
        }

    except Exception as e:
        return {"error": str(e)}


# ----------------------------------------------------
# Submit Audio Answer Endpoint (PARALLELIZED)
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


        # ====================================================
        # STAGE 1: STT via Groq Whisper (fast cloud)
        # ====================================================

        print("=" * 50)
        print("🎤 STAGE 1: Speech-to-Text (Groq Cloud)...")

        stt_start = time.time()
        text, timestamps = await asyncio.to_thread(
            speech_pipeline.transcribe, path
        )
        print(f"⏱  STT Time: {time.time() - stt_start:.2f}s")

        transcript = text if text else ""

        if not transcript.strip():
            return {
                "transcript": "",
                "fluency_score": 0,
                "next_question": "Could you please repeat your answer?"
            }


        # ====================================================
        # STAGE 2: PARALLEL — Groq LLM + Fluency Analysis
        # ====================================================

        print("🚀 STAGE 2: Running Groq + Analysis in PARALLEL...")

        analysis_start = time.time()

        groq_task = asyncio.to_thread(manager.process_answer, transcript)
        analysis_task = asyncio.to_thread(speech_pipeline.analyze, path, text, timestamps)

        next_question, analysis_result = await asyncio.gather(groq_task, analysis_task)

        print(f"⏱  Analysis Time: {time.time() - analysis_start:.2f}s")


        # ====================================================
        # Return combined response
        # ====================================================

        total_elapsed = time.time() - total_start
        print(f"✅ TOTAL Response Time: {total_elapsed:.2f}s")
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
            "job_role": manager.job_role.get("title", "") if manager.job_role else ""  # ✅ Include in response
        }

    except Exception as e:
        print(f"❌ Server error: {e}")
        return {"error": str(e)}