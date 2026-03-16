# Import OpenAI client
# This allows the system to generate intelligent questions
from openai import OpenAI


# ----------------------------------------------------
# AdaptiveQuestionGenerator
# ----------------------------------------------------

class AdaptiveQuestionGenerator:

    def __init__(self):

        # Initialize OpenAI client
        self.client = OpenAI()


    # ----------------------------------------------------
    # Generate next interview question
    # ----------------------------------------------------

    def generate_question(self, resume_skills, previous_questions, previous_answers):

        # Create a structured prompt for the LLM
        # This prompt gives the model context about the candidate
        prompt = f"""
You are an expert technical interviewer.

Candidate skills: {resume_skills}

Questions already asked: {previous_questions}

Candidate answers: {previous_answers}

Generate the next interview question.

Rules:
- Avoid repeating previous questions
- Increase difficulty gradually
- Ask deeper questions about the candidate's skills
- Mimic a real technical interview
"""


        # Send prompt to the language model
        response = self.client.chat.completions.create(

            # Use lightweight model for cost efficiency
            model="gpt-4.1-mini",

            # Conversation format
            messages=[
                {"role": "user", "content": prompt}
            ]
        )


        # Extract generated question from response
        question = response.choices[0].message.content


        # Return generated question
        return question