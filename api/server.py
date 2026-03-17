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


# ----------------------------------------------------
# Import AI modules
# ----------------------------------------------------

from interview_engine.interview_manager import InterviewManager
from pipelines.evaluation_pipeline import SpeechEvaluationPipeline


# ----------------------------------------------------
# Initialize FastAPI app
# ----------------------------------------------------

app = FastAPI()


# ----------------------------------------------------
# Initialize global systems
# ----------------------------------------------------

# Speech pipeline (shared)
speech_pipeline = SpeechEvaluationPipeline()

# Dictionary to store multiple interview sessions
sessions = {}


# ----------------------------------------------------
# Upload Resume Endpoint (START INTERVIEW)
# ----------------------------------------------------

@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):

    try:

        # Save uploaded resume file
        path = f"temp_{file.filename}"

        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)


        # Create a unique session ID for this candidate
        session_id = str(uuid.uuid4())


        # Create a new interview manager instance
        manager = InterviewManager()


        # Start interview and get first question
        question = manager.start_interview(path)


        # Store session
        sessions[session_id] = manager


        # Return session ID + first question
        return {
            "session_id": session_id,
            "question": question
        }

    except Exception as e:

        return {"error": str(e)}


# ----------------------------------------------------
# Submit Audio Answer Endpoint
# ----------------------------------------------------

@app.post("/submit-answer")
async def submit_answer(
    session_id: str = Form(...),   # session ID required
    file: UploadFile = File(...)
):

    try:

        # ----------------------------------------------------
        # Validate session
        # ----------------------------------------------------

        if session_id not in sessions:
            return {"error": "Invalid session_id"}


        # Get interview manager for this session
        manager = sessions[session_id]


        # ----------------------------------------------------
        # Validate file type (audio only)
        # ----------------------------------------------------

        if not file.filename.endswith((".wav", ".mp3", ".flac", ".ogg")):
            return {"error": "Only audio files (.wav, .mp3, .flac, .ogg) are allowed"}


        # ----------------------------------------------------
        # Save uploaded audio
        # ----------------------------------------------------

        path = f"temp_{file.filename}"

        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)


        # ----------------------------------------------------
        # Run speech evaluation
        # ----------------------------------------------------

        result = speech_pipeline.evaluate(path)

        transcript = result.get("transcript", "")


        # ----------------------------------------------------
        # Process interview logic
        # ----------------------------------------------------

        next_question = manager.process_answer(transcript)


        # ----------------------------------------------------
        # Return response
        # ----------------------------------------------------

        return {
            "transcript": transcript,
            "fluency_score": result.get("fluency_score", 0),
            "next_question": next_question
        }

    except Exception as e:

        # Prevent server crash and return error
        return {"error": str(e)}