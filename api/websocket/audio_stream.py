import asyncio
import logging
import tempfile
import subprocess
import os

from fastapi import WebSocket, WebSocketDisconnect
from services.streaming.audio_buffer import AudioBuffer
from services.streaming.vad import VADProcessor

logger = logging.getLogger(__name__)


# =========================
# AUDIO CONVERSION (WEBM → WAV)
# =========================
def convert_webm_to_wav(audio_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        f.write(audio_bytes)
        input_path = f.name

    output_path = input_path + ".wav"

    command = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        output_path
    ]

    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return output_path


# =========================
# MAIN HANDLER
# =========================
async def handle_audio_stream(websocket: WebSocket, session: dict):

    logger.info("WebSocket connection started")

    buffer = AudioBuffer(
        sample_rate=16000,
        silence_duration_ms=800,
        max_duration_ms=30000,
    )

    vad = VADProcessor(sample_rate=16000, aggressiveness=2)

    from services.stt_service import transcribe_audio
    from interview_engine.evaluator import evaluate_answer
    from question_engine.generator import generate_next_question

    try:
        await websocket.send_json({"type": "ready"})

        while True:
            raw = await websocket.receive_bytes()

            print("Received chunk:", len(raw))

            # STOP SIGNAL
            if raw == b"__END__":
                audio_bytes = buffer.flush()
                buffer.reset()

                if audio_bytes:
                    await process_audio(
                        websocket, audio_bytes, session,
                        transcribe_audio, evaluate_answer, generate_next_question
                    )
                continue

            # ⚠️ IMPORTANT: SKIP VAD (because input is WebM)
            buffer.chunks.append(raw)

            # PROCESS every ~2 seconds (simple approach)
            if len(buffer.chunks) >= 10:
                audio_bytes = b"".join(buffer.chunks)
                buffer.reset()

                await process_audio(
                    websocket, audio_bytes, session,
                    transcribe_audio, evaluate_answer, generate_next_question
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")

    except Exception as e:
        logger.exception("Error in stream")
        await websocket.send_json({"type": "error", "message": str(e)})

    finally:
        buffer.reset()


# =========================
# PROCESS AUDIO
# =========================
async def process_audio(
    websocket: WebSocket,
    audio_bytes: bytes,
    session: dict,
    transcribe_audio,
    evaluate_answer,
    generate_next_question,
):
    await websocket.send_json({"type": "processing"})

    loop = asyncio.get_event_loop()

    # 🔥 Convert WebM → WAV
    wav_path = convert_webm_to_wav(audio_bytes)

    try:
        # STT
        transcript = await loop.run_in_executor(
            None, transcribe_audio, wav_path
        )

        print("Transcript:", transcript)

        await websocket.send_json({
            "type": "transcript",
            "text": transcript
        })

        if not transcript.strip():
            await websocket.send_json({
                "type": "result",
                "message": "Could not understand audio"
            })
            return

        # AI Evaluation
        current_question = session.get("current_question", "")

        evaluation = await loop.run_in_executor(
            None, evaluate_answer, transcript, current_question, session
        )

        next_question = await loop.run_in_executor(
            None, generate_next_question, transcript, evaluation, session
        )

        # Update session
        session["current_question"] = next_question
        session.setdefault("history", []).append({
            "answer": transcript,
            "evaluation": evaluation,
            "next_question": next_question,
        })

        # Send final response
        await websocket.send_json({
            "type": "result",
            "transcript": transcript,
            "evaluation": evaluation,
            "next_question": next_question,
        })

    finally:
        # Cleanup files
        if os.path.exists(wav_path):
            os.remove(wav_path)