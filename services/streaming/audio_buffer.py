"""
services/streaming/audio_buffer.py

Accumulates raw PCM chunks (16-bit, mono, 16 kHz) and signals when a
complete utterance has been captured, using a silence-duration threshold
and an absolute max-duration guard.
"""

import io
import wave
import struct
from collections import deque


class AudioBuffer:
    """
    Collect PCM audio frames and decide when an utterance is complete.

    Strategy
    --------
    - Keep a rolling deque of the last N frames to detect silence.
    - When speech starts, collect all incoming frames.
    - When silence_duration_ms of consecutive silence follows speech,
      the utterance is considered complete.
    - Hard-stop at max_duration_ms regardless of VAD state.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        silence_duration_ms: int = 800,
        max_duration_ms: int = 30_000,
        frame_duration_ms: int = 30,   # must match what VAD / browser sends
    ):
        self.sample_rate = sample_rate
        self.silence_duration_ms = silence_duration_ms
        self.max_duration_ms = max_duration_ms
        self.frame_duration_ms = frame_duration_ms

        # Derived counts
        self._silence_frames_needed = silence_duration_ms // frame_duration_ms
        self._max_frames = max_duration_ms // frame_duration_ms

        self._frames: list[bytes] = []
        self._silence_frame_count: int = 0
        self._speech_started: bool = False
        self._total_frames: int = 0

    # ── Public API ──────────────────────────────────────────────────────────

    def add_chunk(self, pcm_frame: bytes, is_speech: bool) -> bool:
        """
        Append a PCM frame and return True when the utterance is complete.

        Parameters
        ----------
        pcm_frame : bytes
            Raw 16-bit little-endian PCM audio for one frame.
        is_speech : bool
            VAD verdict for this frame.

        Returns
        -------
        bool
            True  → utterance complete; call flush() then reset().
            False → still accumulating.
        """
        self._total_frames += 1

        if is_speech:
            self._speech_started = True
            self._silence_frame_count = 0
            self._frames.append(pcm_frame)
        else:
            if self._speech_started:
                # Keep silence frames so the audio doesn't clip abruptly
                self._frames.append(pcm_frame)
                self._silence_frame_count += 1

                if self._silence_frame_count >= self._silence_frames_needed:
                    return True   # ← utterance complete (silence timeout)

        # Hard cap
        if self._total_frames >= self._max_frames and self._speech_started:
            return True

        return False

    def flush(self) -> bytes:
        """
        Return all buffered audio as a valid WAV file in bytes.
        Returns empty bytes if no speech was captured.
        """
        if not self._frames:
            return b""

        raw_pcm = b"".join(self._frames)
        return _pcm_to_wav(raw_pcm, self.sample_rate)

    def reset(self):
        """Clear the buffer for the next utterance."""
        self._frames.clear()
        self._silence_frame_count = 0
        self._speech_started = False
        self._total_frames = 0

    @property
    def has_speech(self) -> bool:
        return self._speech_started and len(self._frames) > 0


# ── Helpers ─────────────────────────────────────────────────────────────────

def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int, channels: int = 1) -> bytes:
    """Wrap raw 16-bit PCM in a proper WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)          # 16-bit = 2 bytes per sample
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()