# ----------------------------------------------------
# Import OpenAI client
# ----------------------------------------------------

# The OpenAI client allows us to send prompts to an LLM
# which will analyze the candidate's answer
from openai import OpenAI


# ----------------------------------------------------
# AnswerEvaluator Class
# ----------------------------------------------------

class AnswerEvaluator:


    # ----------------------------------------------------
    # Constructor
    # ----------------------------------------------------

    # This function runs when the class is initialized
    def __init__(self):

        # Initialize OpenAI client
        self.client = OpenAI()


    # ----------------------------------------------------
    # Evaluate candidate answer
    # ----------------------------------------------------

    def evaluate(self, question, answer):

        # ----------------------------------------------------
        # Create prompt for the AI model
        # ----------------------------------------------------

        # This prompt instructs the AI to behave like
        # an experienced technical interviewer
        prompt = f"""
You are a senior technical interviewer.

Question asked:
{question}

Candidate answer:
{answer}

Evaluate the answer using the following metrics:

1. Correctness (0-10)
2. Completeness (0-10)
3. Depth of explanation (0-10)
4. Clarity of explanation (0-10)

Then provide short feedback explaining strengths and weaknesses.

Return the result in JSON format.
"""


        # ----------------------------------------------------
        # Send prompt to OpenAI model
        # ----------------------------------------------------

        response = self.client.chat.completions.create(

            # Lightweight model suitable for production
            model="gpt-4.1-mini",

            # Chat format messages
            messages=[
                {"role": "system", "content": "You are an expert technical interviewer."},
                {"role": "user", "content": prompt}
            ]
        )


        # ----------------------------------------------------
        # Extract model response
        # ----------------------------------------------------

        # The model returns structured evaluation text
        result = response.choices[0].message.content


        # Return evaluation result
        return result