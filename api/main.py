# Import the FastAPI framework which is used to build APIs in Python
from fastapi import FastAPI, UploadFile, File
import os
import subprocess

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

    wav_path = temp_audio_path + ".wav"

    try:

        # Convert uploaded file to 16kHz mono WAV using ffmpeg
        conversion = subprocess.run(
            [
                r"C:\ffmpeg\bin\ffmpeg.exe",
                "-y",
                "-i", temp_audio_path,
                "-ar", "16000",
                "-ac", "1",
                wav_path
            ],
            capture_output=True,
            text=True
        )

        # If conversion fails return error
        if conversion.returncode != 0:
            return {"error": conversion.stderr}

        # Call the evaluation pipeline and pass the path of the saved audio file
        # The pipeline will process the audio and compute speech metrics
        result = pipeline.evaluate(wav_path)

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

        if os.path.exists(wav_path):
            os.remove(wav_path)