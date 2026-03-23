# ----------------------------------------------------
# Import resume parser
# ----------------------------------------------------

from resume_parser.parser import ResumeParser
from knowledge_engine.topic_graph import TopicGraph
from knowledge_engine.topic_tracker import TopicTracker
from interview_engine.interview_state import InterviewState
from interview_engine.interview_flow_controller import InterviewFlowController
from interview_engine.difficulty_controller import DifficultyController
from resume_parser.skill_extractor import SkillExtractor
from question_engine.question_generator import QuestionGenerator
from question_engine.followup_generator import FollowUpGenerator

# ✅ NEW: Import job role config
from configs.job_roles import get_role


# ----------------------------------------------------
# InterviewManager Class
# ----------------------------------------------------

class InterviewManager:

    def __init__(self):

        self.parser = ResumeParser()
        self.skill_extractor = SkillExtractor()
        self.question_generator = QuestionGenerator()
        self.followup_generator = FollowUpGenerator()
        self.state = InterviewState()
        self.flow = InterviewFlowController()
        self.difficulty = DifficultyController()
        self.topic_graph = TopicGraph()
        self.topic_tracker = TopicTracker()

        self.skills = []
        self.questions_asked = []
        self.answers = []
        self.current_question_index = 0

        # ✅ NEW: Job role context (set during start_interview)
        self.job_role = None
        self.job_role_key = None


    # ----------------------------------------------------
    # Start interview — now accepts job_role_key
    # ----------------------------------------------------

    def start_interview(self, resume_path, job_role_key="software_engineer"):

        # ✅ Load job role config
        self.job_role_key = job_role_key
        self.job_role = get_role(job_role_key)

        print(f"🎯 Job Role: {self.job_role['title']}")

        # Step 1: Extract resume text
        resume_text = self.parser.extract_text(resume_path)

        # Step 2: Extract candidate skills from resume
        self.skills = self.skill_extractor.extract_skills(resume_text)

        # ✅ Merge resume skills with role's focus skills (deduplicated)
        role_skills = self.job_role.get("focus_skills", [])
        combined_skills = list(dict.fromkeys(self.skills + role_skills))
        self.skills = combined_skills

        self.state.skills = self.skills
        # ✅ Also store role in state
        self.state.job_role = self.job_role

        print("Detected skills:", self.skills)

        stage = self.flow.get_current_stage()

        role_title = self.job_role["title"]

        # ----------------------------------------------------
        # Stage 1: Introduction — mention the role
        # ----------------------------------------------------

        if stage == "introduction":
            question = f"Could you briefly introduce yourself and tell me why you're interested in the {role_title} role?"

        # ----------------------------------------------------
        # Stage 2: Resume discussion
        # ----------------------------------------------------

        elif stage == "resume_discussion":
            if len(self.skills) > 0:
                question = f"I see you have experience with {self.skills[0]}. How does that relate to your interest in the {role_title} position?"
            else:
                question = f"Can you describe a technical project relevant to the {role_title} role?"

        # ----------------------------------------------------
        # Stage 3: Skill validation — role-focused
        # ----------------------------------------------------

        elif stage == "skill_validation":
            questions = self.question_generator.generate_questions(self.skills)
            question = questions[0] if questions else f"Explain a core concept important for a {role_title}."

        # ----------------------------------------------------
        # Stage 4: Deep technical — role-specific topic
        # ----------------------------------------------------

        elif stage == "deep_technical":
            key_topics = self.job_role.get("key_topics", [])
            if key_topics:
                question = f"Can you explain your understanding of {key_topics[0]} as it applies to a {role_title} role?"
            elif len(self.skills) > 0:
                question = f"Can you explain an advanced concept in {self.skills[0]}?"
            else:
                question = "Can you explain how you would design a scalable software system?"

        # ----------------------------------------------------
        # Stage 5: Scenario — role-specific
        # ----------------------------------------------------

        elif stage == "scenario":
            key_topics = self.job_role.get("key_topics", [])
            topic = key_topics[1] if len(key_topics) > 1 else "your area of expertise"
            question = f"Suppose you're working as a {role_title} and face a critical issue with {topic}. How would you handle it?"

        # ----------------------------------------------------
        # Stage 6: Behavioral
        # ----------------------------------------------------

        elif stage == "behavioral":
            question = f"Tell me about a time you solved a challenging problem relevant to {role_title} work."

        # ----------------------------------------------------
        # Stage 7: Closing
        # ----------------------------------------------------

        else:
            question = f"Do you have any questions about the {role_title} role or the team?"

        self.questions_asked.append(question)
        self.state.add_question(question)

        return question


    # ----------------------------------------------------
    # Get current question
    # ----------------------------------------------------

    def get_current_question(self):

        if self.current_question_index < len(self.questions_asked):
            return self.questions_asked[self.current_question_index]
        return None


    # ----------------------------------------------------
    # Process candidate answer — passes role context
    # ----------------------------------------------------

    def process_answer(self, answer):

        self.answers.append(answer)
        self.state.add_answer(answer)

        question = self.questions_asked[self.current_question_index]
        difficulty_level = self.difficulty.update_difficulty()

        print("Current difficulty:", difficulty_level)

        # ✅ Pass job role into follow-up generator
        followup = self.followup_generator.generate_followup(
            question,
            answer,
            skills=self.skills,
            previous_questions=self.questions_asked,
            job_role=self.job_role          # ✅ NEW
        )

        self.questions_asked.append(followup)
        self.state.add_question(followup)
        self.current_question_index += 1

        if self.current_question_index % 3 == 0:
            next_stage = self.flow.next_stage()
            print("Moving to interview stage:", next_stage)

        return followup