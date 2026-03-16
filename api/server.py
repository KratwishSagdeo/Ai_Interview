from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File
import shutil
import os

from interview_engine.interview_manager import InterviewManager
from pipelines.evaluation_pipeline import SpeechEvaluationPipeline


# ----------------------------------------------------
# Initialize FastAPI app
# ----------------------------------------------------

app = FastAPI()


# ----------------------------------------------------
# Initialize AI systems
# ----------------------------------------------------

interview_manager = InterviewManager()
speech_pipeline = SpeechEvaluationPipeline()


# Store current interview session
current_question = None


# ----------------------------------------------------
# Upload Resume Endpoint
# ----------------------------------------------------

@app.post("/upload-resume")

async def upload_resume(file: UploadFile = File(...)):

    # Save uploaded resume
    path = f"temp_{file.filename}"

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Start interview
    question = interview_manager.start_interview(path)

    global current_question
    current_question = question

    return {"question": question}


# ----------------------------------------------------
# Submit Audio Answer
# ----------------------------------------------------

@app.post("/submit-answer")

async def submit_answer(file: UploadFile = File(...)):

    # Save audio answer
    path = f"temp_{file.filename}"

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run speech evaluation
    result = speech_pipeline.evaluate(path)

    transcript = result["transcript"]

    # Send transcript to interview manager
    next_question = interview_manager.process_answer(transcript)

    return {
        "transcript": transcript,
        "fluency_score": result["fluency_score"],
        "next_question": next_question
    }