# ----------------------------------------------------
# Add project root directory to Python import path
# ----------------------------------------------------

# Import the sys module
# sys allows us to modify the Python runtime environment
import sys

# Import os module
# os is used to work with file paths and directories
import os

# Append the parent directory of this script to Python's module search path
# This ensures Python can find modules like pipelines/, audio/, nlp/, etc.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ----------------------------------------------------
# Import required libraries
# ----------------------------------------------------

# Import json module
# json is used to read the dataset label file (scores.json)
import json

# Import pandas library
# pandas is used to create and manipulate tabular datasets
import pandas as pd

# Import the SpeechEvaluationPipeline class
# This pipeline contains the logic for:
# speech recognition
# pause detection
# grammar analysis
# lexical diversity
from pipelines.evaluation_pipeline import SpeechEvaluationPipeline


# ----------------------------------------------------
# Initialize the evaluation pipeline
# ----------------------------------------------------

# Create an instance of the SpeechEvaluationPipeline
# This loads all modules used for feature extraction
pipeline = SpeechEvaluationPipeline()


# ----------------------------------------------------
# Define dataset locations
# ----------------------------------------------------

# Root folder containing the dataset
DATASET_ROOT = "datasets/speechocean762"

# Path to the folder containing all audio files
# Inside this folder there are multiple speaker folders
AUDIO_ROOT = os.path.join(DATASET_ROOT, "WAVE")

# Path to the label file containing fluency scores
LABEL_FILE = os.path.join(DATASET_ROOT, "resource", "scores.json")


# ----------------------------------------------------
# Load dataset labels
# ----------------------------------------------------

# Open the JSON label file
with open(LABEL_FILE, "r") as f:

    # Load JSON data into a Python dictionary
    # The dictionary maps audio_id → score information
    scores = json.load(f)


# ----------------------------------------------------
# Storage for dataset rows
# ----------------------------------------------------

# Create an empty list
# Each element of this list will represent one training sample
rows = []


# ----------------------------------------------------
# Traverse all speaker folders
# ----------------------------------------------------

# Loop through every folder inside the WAVE directory
# Example folder: SPEAKER0001
for speaker in os.listdir(AUDIO_ROOT):

    # Build the full path to the speaker folder
    speaker_path = os.path.join(AUDIO_ROOT, speaker)

    # Check whether the current item is actually a directory
    # If not, skip it
    if not os.path.isdir(speaker_path):
        continue


    # ----------------------------------------------------
    # Process each audio file in the speaker folder
    # ----------------------------------------------------

    # Loop through every audio file inside the speaker folder
    for audio_file in os.listdir(speaker_path):

        # Skip files that are not WAV files
        if not audio_file.endswith(".WAV"):
            continue

        # Build the full path to the audio file
        audio_path = os.path.join(speaker_path, audio_file)

        # Extract the audio ID
        # Example: "000010011.WAV" → "000010011"
        audio_id = audio_file.replace(".WAV", "")

        # Check whether this audio file exists in the label dictionary
        if audio_id not in scores:
            continue


        try:

            # ----------------------------------------------------
            # Run feature extraction pipeline
            # ----------------------------------------------------

            # Pass the audio file into the evaluation pipeline
            # This returns speech analysis results
            result = pipeline.evaluate(audio_path)

            # Check if transcript is empty
            # Empty transcripts can break speech feature calculations
            if result["transcript"] == "":
                continue


            # ----------------------------------------------------
            # Build dataset row
            # ----------------------------------------------------

            # Safely extract fluency score from label dictionary
            # This prevents crashes if JSON structure is slightly different
            fluency_score = scores[audio_id].get("fluency", None)

            # Skip sample if fluency score is missing
            if fluency_score is None:
                continue

            # Create a dictionary containing training features
            row = {

                # Words per minute speaking speed
                "speech_rate": result["speech_rate"],

                # Number of pauses detected in speech
                "pause_count": result["pause_count"],

                # Number of filler words like "um", "uh"
                "filler_count": result["filler_count"],

                # Number of grammar mistakes detected
                "grammar_errors": result["grammar_errors"],

                # Vocabulary diversity score
                "lexical_diversity": result["lexical_diversity"],

                # Ground truth fluency score from dataset
                "fluency_score": fluency_score
            }


            # Add the row to the dataset list
            rows.append(row)

            # Print progress message
            print("Processed:", audio_id)


        except Exception as e:

            # If any error occurs during processing,
            # print the error and skip the file
            print("Error processing:", audio_id, e)


# ----------------------------------------------------
# Convert dataset rows into a DataFrame
# ----------------------------------------------------

# Create a pandas DataFrame from the list of dictionaries
dataset = pd.DataFrame(rows)


# ----------------------------------------------------
# Save dataset to CSV file
# ----------------------------------------------------

# Build output file path inside training directory
output_file = os.path.join(os.path.dirname(__file__), "training_dataset.csv")

# Save the dataset as a CSV file
# index=False prevents pandas from adding an extra index column
dataset.to_csv(output_file, index=False)


# ----------------------------------------------------
# Final confirmation message
# ----------------------------------------------------

# Print a message indicating dataset creation is complete
print("Dataset built successfully.")