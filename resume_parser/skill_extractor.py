# Import spacy NLP library
# Used for natural language processing
import spacy


# Load English NLP model
nlp = spacy.load("en_core_web_sm")


# ----------------------------------------------------
# SkillExtractor Class
# ----------------------------------------------------

class SkillExtractor:

    def __init__(self):

        # Define a list of known technical skills
        self.skill_keywords = [
            "python",
            "java",
            "c++",
            "machine learning",
            "deep learning",
            "tensorflow",
            "pytorch",
            "docker",
            "kubernetes",
            "aws",
            "sql",
            "data structures",
            "algorithms",
            "cybersecurity",
            "network security",
            "nlp"
        ]


    # ----------------------------------------------------
    # Extract skills from resume text
    # ----------------------------------------------------

    def extract_skills(self, resume_text):

        # Convert text to lowercase
        # This ensures matching works correctly
        text = resume_text.lower()

        # List to store detected skills
        detected_skills = []

        # Loop through all skill keywords
        for skill in self.skill_keywords:

            # Check if the skill appears in the resume text
            if skill in text:

                # Add the skill to the detected list
                detected_skills.append(skill)

        # Remove duplicates
        detected_skills = list(set(detected_skills))

        # Return list of detected skills
        return detected_skills