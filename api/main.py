from fastapi import FastAPI
import numpy as np

from pipelines.evaluation_pipeline import SpeechEvaluationPipeline

app = FastAPI()

pipeline = SpeechEvaluationPipeline()


@app.post("/evaluate")

async def evaluate(audio: list):

    audio_np = np.array(audio, dtype=np.float32)

    result = pipeline.evaluate(audio_np)

    return result