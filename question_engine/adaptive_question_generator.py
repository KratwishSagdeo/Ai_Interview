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

    def generate_question(self, resume_skills, previous_questions, previous_answers, experience_level="beginner"):

        # Create a structured prompt for the LLM
        # This prompt gives the model context about the candidate
        
        level_instructions = ""
        if experience_level == "beginner":
            level_instructions = "Focus on fundamentals. Avoid complex system design."
        elif experience_level == "intermediate":
            level_instructions = "Include debugging, optimization, and practical application."
        elif experience_level == "expert":
            level_instructions = "Include system design, scaling, trade-offs, and architecture."
        prompt = f"""
You are an expert technical interviewer.

Experience Level: {experience_level}
{level_instructions}

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