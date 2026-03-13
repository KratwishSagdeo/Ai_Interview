# Import the FastAPI framework which is used to build APIs in Python
from fastapi import FastAPI, UploadFile, File
import os

# Import the tempfile module which allows us to create temporary files safely
import tempfile

# Import the main speech evaluation pipeline that contains all processing logic
# This pipeline will handle speech recognition, pause detection, grammar checking etc.
from pipelines.evaluation_pipeline import SpeechEvaluationPipeline


# Create an instance of the FastAPI application
# This object represents our API server
app = FastAPI()


# Create an instance of the SpeechEvaluationPipeline class
# This loads all the modules needed to evaluate speech
pipeline = SpeechEvaluationPipeline()


# Create a GET endpoint at the root URL "/"
# When someone visits http://localhost:8000/ this function will run
@app.get("/")
def home():

    # Return a simple JSON message confirming the API is running
    return {"message": "AI Interview Evaluation API running"}


# Create a POST endpoint called "/evaluate"
# POST is used because we are sending data (audio file) to the server
@app.post("/evaluate")

# Define an asynchronous function named evaluate
# async is used because file upload and reading can be asynchronous operations
async def evaluate(audio: UploadFile = File(...)):

    # Create a temporary file to store the uploaded audio
    # delete=False means the file will not automatically delete after closing
    # suffix=".wav" ensures the temporary file has a .wav extension
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename)[1]) as tmp:

        # Read the uploaded audio file contents asynchronously
        contents = await audio.read()

        # Write the uploaded audio bytes into the temporary file
        tmp.write(contents)

        # Save the temporary file path so we can pass it to the evaluation pipeline
        temp_audio_path = tmp.name

    try:

        # Call the evaluation pipeline and pass the path of the saved audio file
        # The pipeline will process the audio and compute speech metrics
        result = pipeline.evaluate(temp_audio_path)

        # Return the evaluation results as a JSON response
        # FastAPI automatically converts Python dictionaries to JSON
        return result

    except Exception as e:

        # Print the error in the server terminal for debugging
        print("Error during evaluation:", e)

        # Return error information instead of crashing the API
        return {"error": str(e)}

    finally:

        # Ensure temporary file is always deleted even if an error occurs
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)



# ---------------------------------------------------------
# End of File Explanation
# ---------------------------------------------------------

# This file is responsible for exposing your speech evaluation system as a REST API.

# Main responsibilities of this file:
# 1. Start a FastAPI server
# 2. Accept audio file uploads from users
# 3. Temporarily save uploaded audio files
# 4. Pass the audio file to the SpeechEvaluationPipeline
# 5. Return the computed evaluation results as JSON

# This file DOES NOT contain the evaluation logic itself.
# The actual speech processing happens inside:
# pipelines/evaluation_pipeline.py

# Typical request flow:
# User → POST /evaluate with audio file → FastAPI
# FastAPI → saves file → calls SpeechEvaluationPipeline
# Pipeline → processes audio → returns metrics
# FastAPI → sends JSON response back to the user

# Example API response:
# {
#   "transcript": "Hello my name is Aryan...",
#   "fluency_score": 82,
#   "speech_rate": 135,
#   "pause_count": 4,
#   "filler_count": 2,
#   "grammar_errors": 1,
#   "lexical_diversity": 0.64
# }