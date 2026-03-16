# ----------------------------------------------------
# Import required libraries
# ----------------------------------------------------

# librosa is a Python library used for audio analysis
# It provides functions to load audio files and compute audio features
import librosa

# numpy is used for numerical computations and arrays
# It is required for operations like mean, variance and combining features
import numpy as np


# ----------------------------------------------------
# Feature Extraction Function
# ----------------------------------------------------

# This function takes the path of an audio file
# and converts the audio into numerical features that ML models can use
def extract_features(audio_path):

    # ----------------------------------------------------
    # Load audio file
    # ----------------------------------------------------

    # librosa.load reads the audio waveform from disk
    # signal → array containing audio amplitude values
    # sr → sampling rate (number of samples per second)
    # sr=16000 forces all audio to be resampled to 16kHz
    signal, sr = librosa.load(audio_path, sr=16000)


    # ----------------------------------------------------
    # MFCC features
    # ----------------------------------------------------

    # MFCC (Mel Frequency Cepstral Coefficients)
    # These represent the spectral shape of human speech
    # n_mfcc=13 means we extract 13 MFCC coefficients
    mfcc = librosa.feature.mfcc(y=signal, sr=sr, n_mfcc=13)

    # MFCC values vary over time
    # We take the mean of each coefficient across time
    # axis=1 means average along the time dimension
    mfcc_mean = np.mean(mfcc, axis=1)


    # ----------------------------------------------------
    # Zero Crossing Rate
    # ----------------------------------------------------

    # Zero Crossing Rate measures how often the signal crosses zero
    # It helps capture speech noisiness and articulation patterns
    zcr = np.mean(librosa.feature.zero_crossing_rate(signal))


    # ----------------------------------------------------
    # Spectral Centroid
    # ----------------------------------------------------

    # Spectral centroid represents the "center of mass" of frequencies
    # It indicates where most of the energy of the signal is located
    # Higher centroid → brighter sound
    spectral_centroid = np.mean(
        librosa.feature.spectral_centroid(y=signal, sr=sr)
    )


    # ----------------------------------------------------
    # Spectral Bandwidth
    # ----------------------------------------------------

    # Spectral bandwidth measures how spread out the frequencies are
    # It helps detect speech clarity and articulation variation
    spectral_bandwidth = np.mean(
        librosa.feature.spectral_bandwidth(y=signal, sr=sr)
    )


    # ----------------------------------------------------
    # RMS Energy
    # ----------------------------------------------------

    # RMS (Root Mean Square) energy represents loudness of speech
    # It measures the average energy level of the audio signal
    rms = librosa.feature.rms(y=signal)

    # Mean energy across the audio
    rms_mean = np.mean(rms)

    # Variance of energy shows how much loudness changes
    energy_variance = np.var(rms)


    # ----------------------------------------------------
    # Pitch Extraction
    # ----------------------------------------------------

    # piptrack extracts pitch frequencies present in the signal
    # pitches → frequency values
    # magnitudes → strength of each frequency
    pitches, magnitudes = librosa.piptrack(y=signal, sr=sr)

    # Extract only valid pitch values (non-zero)
    pitch_values = pitches[pitches > 0]

    # If pitch values exist calculate statistics
    if len(pitch_values) > 0:

        # Mean pitch across the audio
        pitch_mean = np.mean(pitch_values)

        # Variance of pitch indicates prosody variation
        pitch_variance = np.var(pitch_values)

    else:

        # If pitch cannot be detected set features to zero
        pitch_mean = 0
        pitch_variance = 0


    # ----------------------------------------------------
    # Pause Detection
    # ----------------------------------------------------

    # Convert signal amplitude to absolute values
    energy = np.abs(signal)

    # Compute a silence threshold using the 10th percentile
    threshold = np.percentile(energy, 10)

    # Detect silent frames where energy is below threshold
    silence_frames = energy < threshold

    # Calculate pause duration in seconds
    pause_duration = np.sum(silence_frames) / sr


    # ----------------------------------------------------
    # Speaking Ratio
    # ----------------------------------------------------

    # Total duration of audio in seconds
    total_duration = len(signal) / sr

    # Speaking ratio = speech time / total audio time
    speaking_ratio = 1 - (pause_duration / total_duration)


    # ----------------------------------------------------
    # Combine all features into one vector
    # ----------------------------------------------------

    # np.hstack merges all features into one numerical array
    # This array becomes the input to the machine learning model
    features = np.hstack([

        # MFCC features (13 values)
        mfcc_mean,

        # Zero crossing rate
        zcr,

        # Spectral centroid
        spectral_centroid,

        # Spectral bandwidth
        spectral_bandwidth,

        # Mean speech energy
        rms_mean,

        # Energy variation
        energy_variance,

        # Pitch statistics
        pitch_mean,
        pitch_variance,

        # Pause related features
        pause_duration,
        speaking_ratio
    ])


    # ----------------------------------------------------
    # Return feature vector
    # ----------------------------------------------------

    # This vector will be used as input to XGBoost
    return features