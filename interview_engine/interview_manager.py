# ----------------------------------------------------
# Import resume parser
# ----------------------------------------------------

# This module extracts raw text from the uploaded resume
from resume_parser.parser import ResumeParser
from knowledge_engine.topic_graph import TopicGraph
from knowledge_engine.topic_tracker import TopicTracker

# Import interview state manager
# This stores the state of the interview such as
# questions asked, answers given, topics covered
from interview_engine.interview_state import InterviewState


# Import interview flow controller
# This controls interview stages like introduction,
# resume discussion, technical questions etc.
from interview_engine.interview_flow_controller import InterviewFlowController


# Import difficulty controller
# This adjusts question difficulty as interview progresses
from interview_engine.difficulty_controller import DifficultyController


# ----------------------------------------------------
# Import skill extractor
# ----------------------------------------------------

# This module analyzes resume text and detects technical skills
from resume_parser.skill_extractor import SkillExtractor


# ----------------------------------------------------
# Import question generator
# ----------------------------------------------------

# This module generates technical questions based on skills
from question_engine.question_generator import QuestionGenerator


# ----------------------------------------------------
# Import follow-up generator
# ----------------------------------------------------

# This module generates deeper follow-up questions
from question_engine.followup_generator import FollowUpGenerator


# ----------------------------------------------------
# InterviewManager Class
# ----------------------------------------------------

# This class controls the entire interview process
class InterviewManager:


    # ----------------------------------------------------
    # Constructor
    # ----------------------------------------------------

    # This function runs automatically when the class is created
    def __init__(self):

        # Initialize resume parser
        self.parser = ResumeParser()

        # Initialize skill extractor
        self.skill_extractor = SkillExtractor()

        # Initialize technical question generator
        self.question_generator = QuestionGenerator()

        # Initialize follow-up generator
        self.followup_generator = FollowUpGenerator()

        # Initialize interview state tracker
        self.state = InterviewState()

        # Initialize interview flow controller
        self.flow = InterviewFlowController()

        # Initialize difficulty controller
        self.difficulty = DifficultyController()
        self.topic_graph = TopicGraph()
        self.topic_tracker = TopicTracker()

        # ----------------------------------------------------
        # Interview state variables
        # ----------------------------------------------------

        # List to store candidate skills extracted from resume
        self.skills = []

        # List to store questions asked
        self.questions_asked = []

        # List to store candidate answers
        self.answers = []

        # Index of current question
        self.current_question_index = 0


    # ----------------------------------------------------
    # Start interview
    # ----------------------------------------------------

    def start_interview(self, resume_path):

        # Step 1: Extract resume text from PDF
        resume_text = self.parser.extract_text(resume_path)

        # Step 2: Extract candidate skills from resume
        self.skills = self.skill_extractor.extract_skills(resume_text)

        # Save skills in interview state
        self.state.skills = self.skills

        # Print skills for debugging
        print("Detected skills:", self.skills)

        # Step 3: Get current interview stage
        stage = self.flow.get_current_stage()


        # ----------------------------------------------------
        # Stage 1: Introduction
        # ----------------------------------------------------

        if stage == "introduction":

            # Ask candidate to introduce themselves
            question = "Could you briefly introduce yourself?"


        # ----------------------------------------------------
        # Stage 2: Resume discussion
        # ----------------------------------------------------

        elif stage == "resume_discussion":

            # If candidate has skills listed
            if len(self.skills) > 0:

                # Ask about the first detected skill
                question = f"I noticed you mentioned {self.skills[0]} in your resume. Could you explain your experience with it?"

            else:

                # Fallback question
                question = "Can you describe one technical project you worked on?"


        # ----------------------------------------------------
        # Stage 3: Skill validation
        # ----------------------------------------------------

        elif stage == "skill_validation":

            # Generate skill-based technical question
            questions = self.question_generator.generate_questions(self.skills)

            # Pick first question
            question = questions[0] if questions else "Explain a technical concept you recently learned."


        # ----------------------------------------------------
        # Stage 4: Deep technical
        # ----------------------------------------------------

        elif stage == "deep_technical":

            # Ask deeper question about previously mentioned skill
            if len(self.skills) > 0:

                question = f"Can you explain an advanced concept related to {self.skills[0]}?"

            else:

                question = "Can you explain how you would design a scalable software system?"


        # ----------------------------------------------------
        # Stage 5: Scenario question
        # ----------------------------------------------------

        elif stage == "scenario":

            question = "Suppose your production system suddenly fails under heavy load. How would you debug the issue?"


        # ----------------------------------------------------
        # Stage 6: Behavioral question
        # ----------------------------------------------------

        elif stage == "behavioral":

            question = "Tell me about a time when you faced a challenging technical problem and how you solved it."


        # ----------------------------------------------------
        # Stage 7: Closing
        # ----------------------------------------------------

        else:

            question = "Do you have any questions for me about the role or the company?"


        # Save question in interview history
        self.questions_asked.append(question)

        # Also store in interview state
        self.state.add_question(question)

        # Return first question
        return question


    # ----------------------------------------------------
    # Get current question
    # ----------------------------------------------------

    def get_current_question(self):

        # If questions remain
        if self.current_question_index < len(self.questions_asked):

            # Return current question
            return self.questions_asked[self.current_question_index]

        # Interview finished
        return None


    # ----------------------------------------------------
    # Process candidate answer
    # ----------------------------------------------------

    def process_answer(self, answer):

        # Store candidate answer
        self.answers.append(answer)

        # Also store in interview state
        self.state.add_answer(answer)

        # Get current question
        question = self.questions_asked[self.current_question_index]

        # Update difficulty level
        difficulty_level = self.difficulty.update_difficulty()

        print("Current difficulty:", difficulty_level)

        # Generate follow-up question
        followup = self.followup_generator.generate_followup(

            question,
            answer,
            skills=self.skills,
            previous_questions=self.questions_asked
        )

        # Save follow-up question
        self.questions_asked.append(followup)

        # Store question in interview state
        self.state.add_question(followup)

        # Move to next question
        self.current_question_index += 1

        # After some questions move interview stage forward
        if self.current_question_index % 3 == 0:

            # Move to next stage
            next_stage = self.flow.next_stage()

            print("Moving to interview stage:", next_stage)

        # Return generated follow-up question
        return followup