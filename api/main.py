# =========================
# IMPORTS
# =========================

from fastapi import FastAPI, UploadFile, File, WebSocket
import os
import subprocess
import tempfile

from pipelines.evaluation_pipeline import SpeechEvaluationPipeline
from api.websocket.audio_stream import handle_audio_stream


# =========================
# APP INITIALIZATION
# =========================

app = FastAPI()


# =========================
# LOAD PIPELINE (AI ENGINE)
# =========================

pipeline = SpeechEvaluationPipeline()


# =========================
# SESSION MANAGEMENT (TEMPORARY)
# =========================

# NOTE: Replace with Redis / MongoDB later
_sessions: dict[str, dict] = {}


def get_or_create_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "session_id": session_id,
            "current_question": "Tell me about yourself.",
            "history": [],
        }
    return _sessions[session_id]


# =========================
# BASIC HEALTH CHECK
# =========================

@app.get("/")
def home():
    return {"message": "AI Interview Evaluation API running"}


# =========================
# EXISTING FILE-BASED API (KEEP THIS)
# =========================

@app.post("/evaluate")
async def evaluate(audio: UploadFile = File(...)):

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename)[1]) as tmp:
        contents = await audio.read()
        tmp.write(contents)
        temp_audio_path = tmp.name

    wav_path = temp_audio_path + ".wav"

    try:
        # Convert to proper format for STT
        conversion = subprocess.run(
            [
                r"C:\ffmpeg\bin\ffmpeg.exe",
                "-y",
                "-i", temp_audio_path,
                "-ar", "16000",
                "-ac", "1",
                wav_path
            ],
            capture_output=True,
            text=True
        )

        if conversion.returncode != 0:
            return {"error": conversion.stderr}

        result = pipeline.evaluate(wav_path)
        return result

    except Exception as e:
        print("Error during evaluation:", e)
        return {"error": str(e)}

    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)


# =========================
# NEW: REAL-TIME AUDIO STREAMING (WEBSOCKET)
# =========================

@app.websocket("/ws/audio/{session_id}")
async def audio_ws(websocket: WebSocket, session_id: str):

    # VERY IMPORTANT: Accept connection
    await websocket.accept()

    # Get session
    session = get_or_create_session(session_id)

    try:
        # Delegate streaming logic
        await handle_audio_stream(websocket, session)

    except Exception as e:
        print("WebSocket error:", e)

    finally:
        # Ensure connection closes safely
        await websocket.close()