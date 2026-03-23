# Import WebRTC Voice Activity Detection library
import webrtcvad
import wave


class PauseDetector:

    def __init__(self):
        # Initialize VAD with aggressiveness level 3 (fastest, most aggressive)
        self.vad = webrtcvad.Vad(3)

    def detect_pauses(self, audio_path):

        try:
            wf = wave.open(audio_path, 'rb')
            sample_rate = wf.getframerate()
            print("Audio sample rate:", sample_rate)

            # ✅ Only support WebRTC-compatible rates: 8000, 16000, 32000, 48000
            # If sample rate is not supported, skip VAD entirely
            if sample_rate not in (8000, 16000, 32000, 48000):
                wf.close()
                print("Detected pauses: 0 (unsupported sample rate, skipped)")
                return 0

            # ✅ Use 10ms frames instead of 30ms — fewer iterations
            frame_duration = 10
            frame_size = int(sample_rate * frame_duration / 1000)

            pauses = 0
            silent_frames = 0

            # ✅ Read all frames at once instead of one by one
            raw_audio = wf.readframes(wf.getnframes())
            wf.close()

            # Process in chunks
            offset = 0
            chunk = frame_size * 2  # 16-bit = 2 bytes per sample

            while offset + chunk <= len(raw_audio):
                frame = raw_audio[offset:offset + chunk]
                offset += chunk

                try:
                    is_speech = self.vad.is_speech(frame, sample_rate)
                except Exception:
                    continue

                if not is_speech:
                    silent_frames += 1
                else:
                    silence_duration_ms = silent_frames * frame_duration
                    # ✅ Reduced threshold: 1500ms instead of 2500ms
                    if silence_duration_ms >= 1500:
                        pauses += 1
                    silent_frames = 0

            # Handle trailing silence
            if silent_frames * frame_duration >= 1500:
                pauses += 1

            print("Detected pauses:", pauses)
            return pauses

        except Exception as e:
            print(f"⚠️ PauseDetector failed: {e}, returning 0")
            return 0