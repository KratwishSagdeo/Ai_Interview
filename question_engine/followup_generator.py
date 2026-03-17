# ----------------------------------------------------
# Import requests library
# ----------------------------------------------------

# requests is used to send HTTP requests to the local Ollama server
import requests


# ----------------------------------------------------
# FollowUpGenerator Class
# ----------------------------------------------------

class FollowUpGenerator:

    # ----------------------------------------------------
    # Constructor
    # ----------------------------------------------------

    # This function runs when the class is initialized
    def __init__(self):

        # URL of the local Ollama API server
        # Ollama runs on port 11434 by default
        self.url = "http://localhost:11434/api/generate"


    # ----------------------------------------------------
    # Generate follow-up question
    # ----------------------------------------------------

    def generate_followup(self, question, answer, skills=None, previous_questions=None):

        # If skills list is not provided initialize empty list
        if skills is None:
            skills = []

        # If previous_questions list is not provided initialize empty list
        if previous_questions is None:
            previous_questions = []


        # ----------------------------------------------------
        # Construct prompt for the LLM
        # ----------------------------------------------------

        # This prompt instructs the model to behave like a real interviewer
        prompt = f"""
You are a senior technical interviewer.

The candidate previously answered the following question.

Question:
{question}

Candidate Answer:
{answer}

Candidate Skills:
{skills}

Previously Asked Questions:
{previous_questions}

Your task:
1. Analyze the candidate's answer
2. Ask a deeper follow-up question
3. Do NOT repeat previous questions
4. Keep the question short and interview-style
5. Focus on technical depth
"""


        # ----------------------------------------------------
        # Call Ollama API
        # ----------------------------------------------------

        try:

            # Send POST request to Ollama local server
            response = requests.post(

                # API endpoint
                self.url,

                # JSON payload sent to model
                json={
                    "model": "phi3",        # Model name (make sure you ran: ollama run phi3)
                    "prompt": prompt,       # Prompt we created above
                    "stream": False         # Disable streaming (we want full response)
                }
            )


            # Convert response to JSON
            result = response.json()


            # Extract generated text from response
            followup = result.get("response", "").strip()


            # If model returns empty response, fallback
            if not followup:
                followup = "Can you explain that in more detail?"


        except Exception as e:

            # Print error for debugging
            print("Ollama error:", e)

            # Fallback question if something fails
            followup = "Can you explain that in more detail?"


        # ----------------------------------------------------
        # Return follow-up question
        # ----------------------------------------------------

        return followup