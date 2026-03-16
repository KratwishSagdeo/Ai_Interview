# ----------------------------------------------------
# Import OpenAI library
# ----------------------------------------------------

# The OpenAI client is used to communicate with the OpenAI API
# This allows our system to generate intelligent follow-up questions
from openai import OpenAI


# ----------------------------------------------------
# FollowUpGenerator Class
# ----------------------------------------------------

class FollowUpGenerator:

    # Constructor method
    # This runs automatically when the class is initialized
    def __init__(self):

        # Initialize OpenAI API client
        # This object will be used to send prompts to the language model
        self.client = OpenAI()


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
        # Construct the AI prompt
        # ----------------------------------------------------

        # The prompt gives context to the AI model
        # This helps it behave like a real technical interviewer
        prompt = f"""
You are a senior technical interviewer.

The candidate previously answered the following question.

Question asked:
{question}

Candidate answer:
{answer}

Candidate skills:
{skills}

Previously asked questions:
{previous_questions}

Your task:
1. Analyze the candidate's answer
2. Ask a deeper follow-up question
3. The question should probe deeper understanding
4. Do NOT repeat previous questions
5. Keep the question short and interview-style
"""


        # ----------------------------------------------------
        # Call OpenAI model
        # ----------------------------------------------------

        # Send the prompt to the OpenAI model
        # The model will generate a follow-up interview question
        response = self.client.chat.completions.create(

            # Use lightweight model for fast response
            model="gpt-4.1-mini",

            # Messages follow chat format used by OpenAI models
            messages=[
                {"role": "system", "content": "You are an expert technical interviewer."},
                {"role": "user", "content": prompt}
            ]
        )


        # ----------------------------------------------------
        # Extract model response
        # ----------------------------------------------------

        # The model response contains multiple choices
        # We take the first generated message
        followup = response.choices[0].message.content.strip()


        # ----------------------------------------------------
        # Return follow-up question
        # ----------------------------------------------------

        return followup