import wave
import struct
import time
import io


class RealtimeAudioBuffer:
    """
    Buffers incoming raw PCM audio chunks from WebSocket.
    Detects silence to auto-trigger processing.
    Saves buffered audio to a WAV file for Groq Whisper.

    Expected input: 16kHz, mono, 16-bit PCM chunks (raw bytes)
    """

    def __init__(self, sample_rate=16000, silence_threshold=500, silence_duration_sec=1.5):

        self.sample_rate = sample_rate

        # Amplitude below this = silence (0-32768 range for 16-bit)
        # 500 works well for typical microphone input
        self.silence_threshold = silence_threshold

        # How many seconds of silence before auto-triggering
        self.silence_duration_sec = silence_duration_sec

        # Raw PCM bytes buffer
        self.chunks = []

        # Track when silence started
        self.silence_start_time = None

        # Total bytes received (for logging)
        self.total_bytes = 0


    def add_chunk(self, chunk: bytes):
        """Add a raw PCM audio chunk to the buffer."""

        self.chunks.append(chunk)
        self.total_bytes += len(chunk)

        # Check if this chunk is silent
        if self._is_chunk_silent(chunk):
            # Start silence timer if not already started
            if self.silence_start_time is None:
                self.silence_start_time = time.time()
        else:
            # Reset silence timer — candidate is speaking
            self.silence_start_time = None


    def _is_chunk_silent(self, chunk: bytes) -> bool:
        """Returns True if average amplitude of chunk is below threshold."""

        if len(chunk) < 2:
            return True

        try:
            # Unpack 16-bit samples
            num_samples = len(chunk) // 2
            samples = struct.unpack(f"{num_samples}h", chunk[:num_samples * 2])

            # Calculate average absolute amplitude
            avg_amplitude = sum(abs(s) for s in samples) / len(samples)

            return avg_amplitude < self.silence_threshold

        except Exception:
            return True


    def is_silent_long_enough(self) -> bool:
        """
        Returns True if silence has lasted longer than silence_duration_sec.
        Also requires at least some audio has been buffered first.
        """

        # Don't trigger if buffer is nearly empty (< 0.5 seconds of audio)
        min_bytes = self.sample_rate * 2 * 0.5  # 0.5 sec worth of 16-bit samples
        if self.total_bytes < min_bytes:
            return False

        if self.silence_start_time is None:
            return False

        elapsed_silence = time.time() - self.silence_start_time
        return elapsed_silence >= self.silence_duration_sec


    def save_to_wav(self, output_path: str):
        """Save all buffered chunks to a proper WAV file."""

        if not self.chunks:
            raise ValueError("Buffer is empty — nothing to save")

        raw_audio = b"".join(self.chunks)

        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)        # Mono
            wf.setsampwidth(2)        # 16-bit = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(raw_audio)

        duration = len(raw_audio) / (self.sample_rate * 2)
        print(f"💾 Saved {duration:.1f}s of audio to {output_path}")


    def clear(self):
        """Reset buffer after processing."""

        self.chunks = []
        self.total_bytes = 0
        self.silence_start_time = None