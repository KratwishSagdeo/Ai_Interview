# Import random module
# Used to randomly pick questions
import random


# ----------------------------------------------------
# QuestionGenerator Class
# ----------------------------------------------------

class QuestionGenerator:

    def __init__(self):

        # Define question bank for different skills
        self.question_bank = {

            "python": [
                "Explain Python decorators.",
                "What are Python generators?",
                "What is the difference between list and tuple?"
            ],

            "machine learning": [
                "Explain bias vs variance.",
                "What is gradient descent?",
                "How do you prevent overfitting?"
            ],

            "docker": [
                "What problem does Docker solve?",
                "Explain containerization.",
                "How do you deploy an ML model using Docker?"
            ],

            "cybersecurity": [
                "What is a buffer overflow attack?",
                "Explain symmetric vs asymmetric encryption.",
                "What is penetration testing?"
            ]
        }


    # ----------------------------------------------------
    # Generate questions based on skills
    # ----------------------------------------------------

    def generate_questions(self, skills):

        # List to store generated questions
        questions = []

        # Loop through detected skills
        for skill in skills:

            # Check if skill exists in question bank
            if skill in self.question_bank:

                # Randomly choose a question for that skill
                question = random.choice(self.question_bank[skill])

                # Add question to the list
                questions.append(question)

        # Return list of questions
        return questions