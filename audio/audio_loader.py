import librosa


def load_audio(audio_path):
    """
    Loads audio once and normalizes format.

    Returns:
        audio (numpy array)
        sample_rate
    """

    # Load audio
    audio, sr = librosa.load(
        audio_path,
        sr=16000,
        mono=True
    )

    print("Audio loaded. Sample rate:", sr)

    return audio, sr