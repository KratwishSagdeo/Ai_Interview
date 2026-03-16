# ----------------------------------------------------
# InterviewState Class
# ----------------------------------------------------

# This class stores the current state of the interview
# It keeps track of questions, answers, skills, and topics
class InterviewState:


    # ----------------------------------------------------
    # Constructor
    # ----------------------------------------------------

    # This function runs when a new interview starts
    def __init__(self):

        # List of candidate skills extracted from resume
        self.skills = []

        # List of topics already covered during interview
        self.topics_covered = []

        # List of all questions asked so far
        self.questions_asked = []

        # List of candidate answers
        self.answers = []

        # Difficulty level of the interview
        # Starts from easy and increases gradually
        self.difficulty_level = 1

        # Weak areas detected during interview
        self.weak_areas = []


    # ----------------------------------------------------
    # Add new question
    # ----------------------------------------------------

    def add_question(self, question):

        # Store question in list
        self.questions_asked.append(question)


    # ----------------------------------------------------
    # Add candidate answer
    # ----------------------------------------------------

    def add_answer(self, answer):

        # Store answer in answer list
        self.answers.append(answer)


    # ----------------------------------------------------
    # Add topic coverage
    # ----------------------------------------------------

    def add_topic(self, topic):

        # Add topic if not already covered
        if topic not in self.topics_covered:

            self.topics_covered.append(topic)


    # ----------------------------------------------------
    # Increase difficulty level
    # ----------------------------------------------------

    def increase_difficulty(self):

        # Increase difficulty by one step
        self.difficulty_level += 1


    # ----------------------------------------------------
    # Add weak area
    # ----------------------------------------------------

    def add_weak_area(self, topic):

        # Store weak topics where candidate struggled
        if topic not in self.weak_areas:

            self.weak_areas.append(topic)