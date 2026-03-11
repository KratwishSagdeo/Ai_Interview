from fastapi import FastAPI, UploadFile, File
import tempfile

from Ai_Interview.pipelines.evaluation_pipeline import SpeechEvaluationPipeline

app = FastAPI()

pipeline = SpeechEvaluationPipeline()


@app.get("/")
def home():
    return {"message": "AI Interview Evaluation API running"}


@app.post("/evaluate")
async def evaluate(audio: UploadFile = File(...)):

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        contents = await audio.read()
        tmp.write(contents)
        temp_audio_path = tmp.name

    result = pipeline.evaluate(temp_audio_path)

    return result