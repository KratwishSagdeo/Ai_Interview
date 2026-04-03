"""
services/streaming/vad.py

Thin wrapper around webrtcvad (already in your requirements.txt).

webrtcvad expects:
  - 16-bit signed PCM
  - 8000, 16000, or 32000 Hz sample rate
  - Frame sizes of exactly 10, 20, or 30 ms
"""

import webrtcvad


class VADProcessor:
    """
    Classify audio frames as speech or non-speech using WebRTC VAD.

    Parameters
    ----------
    sample_rate : int
        Must be 8000, 16000, or 32000.
    aggressiveness : int
        0 (least aggressive / most permissive) to 3 (most aggressive).
        2 is a good default for mic input in a quiet room.
    frame_duration_ms : int
        Duration of each frame. Must be 10, 20, or 30 ms.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        aggressiveness: int = 2,
        frame_duration_ms: int = 30,
    ):
        assert sample_rate in (8000, 16000, 32000), (
            f"webrtcvad requires 8000/16000/32000 Hz, got {sample_rate}"
        )
        assert frame_duration_ms in (10, 20, 30), (
            f"webrtcvad requires 10/20/30 ms frames, got {frame_duration_ms}"
        )

        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self._expected_bytes = int(sample_rate * (frame_duration_ms / 1000) * 2)  # 16-bit → ×2

        self._vad = webrtcvad.Vad(aggressiveness)

    def is_speech(self, pcm_frame: bytes) -> bool:
        """
        Return True if the frame contains speech.

        The frame MUST be exactly `frame_duration_ms` ms of 16-bit mono PCM.
        If the browser sends a different size (e.g., due to chunking jitter),
        we pad or truncate to the expected length before passing to webrtcvad.
        """
        frame = self._normalize_frame(pcm_frame)
        try:
            return self._vad.is_speech(frame, self.sample_rate)
        except Exception:
            # Fallback: treat as silence if VAD fails on a malformed frame
            return False

    def _normalize_frame(self, frame: bytes) -> bytes:
        """Pad with silence or truncate to the exact expected byte length."""
        expected = self._expected_bytes
        if len(frame) == expected:
            return frame
        if len(frame) < expected:
            return frame + b"\x00" * (expected - len(frame))  # zero-pad
        return frame[:expected]                                 # truncate

    @property
    def expected_frame_bytes(self) -> int:
        """Exact byte length the VAD expects per frame."""
        return self._expected_bytes