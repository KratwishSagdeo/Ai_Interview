"""
services/stt_service.py

Transcription using faster-whisper (local, already in your requirements).
Accepts raw WAV bytes so no temp file is written to disk.
"""

import io
import logging
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Load the model once at import time — reused for every transcription call.
# Swap "base" for "small" or "medium" for better accuracy (costs more RAM/time).
_MODEL = WhisperModel(
    model_size_or_path="base",
    device="cpu",          # change to "cuda" if you have a GPU
    compute_type="int8",   # int8 is fastest on CPU; use "float16" for GPU
)


def transcribe_audio(wav_bytes: bytes, language: str = "en") -> str:
    """
    Transcribe a WAV audio blob and return the transcript as a plain string.

    Parameters
    ----------
    wav_bytes : bytes
        A complete WAV file in memory (as produced by AudioBuffer.flush()).
    language : str
        ISO 639-1 language code. "en" works best for English interviews.

    Returns
    -------
    str
        The full transcript text, or an empty string if nothing was detected.
    """
    if not wav_bytes:
        return ""

    # Decode WAV bytes → numpy float32 array (soundfile handles the header)
    audio_np, sample_rate = sf.read(io.BytesIO(wav_bytes), dtype="float32")

    # faster-whisper expects mono; average channels if stereo
    if audio_np.ndim > 1:
        audio_np = audio_np.mean(axis=1)

    segments, info = _MODEL.transcribe(
        audio_np,
        language=language,
        beam_size=5,
        vad_filter=True,           # built-in VAD filter removes non-speech
        vad_parameters=dict(
            min_silence_duration_ms=300,
        ),
    )

    transcript = " ".join(seg.text.strip() for seg in segments)
    logger.debug(f"Transcribed ({info.language}, {info.duration:.1f}s): {transcript!r}")
    return transcript