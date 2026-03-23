from resume_parser.parser import ResumeParser
from knowledge_engine.topic_graph import TopicGraph
from knowledge_engine.topic_tracker import TopicTracker
from interview_engine.interview_state import InterviewState
from interview_engine.interview_flow_controller import InterviewFlowController
from interview_engine.difficulty_controller import DifficultyController
from resume_parser.skill_extractor import SkillExtractor
from question_engine.question_generator import QuestionGenerator
from question_engine.followup_generator import FollowUpGenerator
from configs.job_roles import get_role
import logging

logger = logging.getLogger("interview_manager")

# ----------------------------------------------------
# Constants
# ----------------------------------------------------

MAX_QUESTIONS = 15          # Hard cap — interview always ends here
MIN_QUESTIONS = 6           # Never end before this many questions
WEAK_SCORE_THRESHOLD = 2    # Filler + grammar errors above this = weak area


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

        self.job_role = None
        self.job_role_key = None

        # ✅ End tracking
        self.is_finished = False
        self.end_reason = None      # "max_questions" | "all_stages_done" | "manual"

        # ✅ Cumulative metrics for final report
        self.metrics_history = []


    # ----------------------------------------------------
    # Start interview
    # ----------------------------------------------------

    def start_interview(self, resume_path, job_role_key="software_engineer"):

        self.job_role_key = job_role_key
        self.job_role = get_role(job_role_key)
        print(f"🎯 Job Role: {self.job_role['title']}")

        resume_text = self.parser.extract_text(resume_path)
        self.skills = self.skill_extractor.extract_skills(resume_text)

        role_skills = self.job_role.get("focus_skills", [])
        self.skills = list(dict.fromkeys(self.skills + role_skills))

        self.state.skills = self.skills
        self.state.job_role = self.job_role
        print("Detected skills:", self.skills)

        stage = self.flow.get_current_stage()
        role_title = self.job_role["title"]

        if stage == "introduction":
            question = f"Could you briefly introduce yourself and tell me why you're interested in the {role_title} role?"
        elif stage == "resume_discussion":
            if self.skills:
                question = f"I see you have experience with {self.skills[0]}. How does that relate to your interest in the {role_title} position?"
            else:
                question = f"Can you describe a technical project relevant to the {role_title} role?"
        elif stage == "skill_validation":
            questions = self.question_generator.generate_questions(self.skills)
            question = questions[0] if questions else f"Explain a core concept important for a {role_title}."
        elif stage == "deep_technical":
            key_topics = self.job_role.get("key_topics", [])
            if key_topics:
                question = f"Can you explain your understanding of {key_topics[0]} as it applies to a {role_title} role?"
            elif self.skills:
                question = f"Can you explain an advanced concept in {self.skills[0]}?"
            else:
                question = "Can you explain how you would design a scalable software system?"
        elif stage == "scenario":
            key_topics = self.job_role.get("key_topics", [])
            topic = key_topics[1] if len(key_topics) > 1 else "your area of expertise"
            question = f"Suppose you're working as a {role_title} and face a critical issue with {topic}. How would you handle it?"
        elif stage == "behavioral":
            question = f"Tell me about a time you solved a challenging problem relevant to {role_title} work."
        else:
            question = f"Do you have any questions about the {role_title} role or the team?"

        self.questions_asked.append(question)
        self.state.add_question(question)
        return question


    # ----------------------------------------------------
    # ✅ Check if interview should end
    # ----------------------------------------------------

    def should_end_interview(self):

        if len(self.questions_asked) >= MAX_QUESTIONS:
            self.end_reason = "max_questions"
            return True

        all_stages_done = self.flow.get_current_stage() == "closing"
        min_reached = len(self.questions_asked) >= MIN_QUESTIONS
        if all_stages_done and min_reached:
            self.end_reason = "all_stages_done"
            return True

        return False


    # ----------------------------------------------------
    # ✅ Process answer — always returns a typed dict
    # ----------------------------------------------------

    def process_answer(self, answer, fluency_metrics=None):
        """
        Returns:
          { "type": "question", "content": "..." }  — next question to ask
          { "type": "end",      "content": "..." }  — interview is over
        """

        self.answers.append(answer)
        self.state.add_answer(answer)

        question = self.questions_asked[self.current_question_index]

        # ✅ Store metrics history for final report
        if fluency_metrics:
            self.metrics_history.append(fluency_metrics)

            # Weak area detection
            fillers = fluency_metrics.get("filler_count", 0)
            grammar = fluency_metrics.get("grammar_errors", 0)
            if fillers + grammar > WEAK_SCORE_THRESHOLD:
                weak_topic = self._get_topic_for_stage(self.flow.get_current_stage())
                if weak_topic:
                    self.state.add_weak_area(weak_topic)
                    logger.warning(f"Weak area detected: {weak_topic}")

        difficulty_level = self.difficulty.update_difficulty()
        logger.info(f"Current difficulty: {difficulty_level}")

        self.current_question_index += 1

        if self.current_question_index % 3 == 0:
            next_stage = self.flow.next_stage()
            logger.info(f"Moving to interview stage: {next_stage}")

        # ✅ Check end condition BEFORE generating a new question
        if self.should_end_interview():
            self.is_finished = True
            logger.info(f"Interview ending — reason: {self.end_reason}")
            return {
                "type": "end",
                "content": "Thank you for your time. That concludes our interview. You will receive your detailed feedback report shortly."
            }

        # ✅ P2: Pass weak_areas for smarter follow-ups + deduplication
        followup = self.followup_generator.generate_followup(
            question,
            answer,
            skills=self.skills,
            previous_questions=self.questions_asked,
            job_role=self.job_role,
            weak_areas=self.state.weak_areas      # ✅ NEW
        )

        self.questions_asked.append(followup)
        self.state.add_question(followup)

        return {
            "type": "question",
            "content": followup
        }


    # ----------------------------------------------------
    # ✅ Generate final report
    # ----------------------------------------------------

    def generate_report(self):
        """Builds a full structured report from the interview session."""

        total_questions = len(self.questions_asked)
        total_answers = len(self.answers)

        # Average all fluency metrics collected during the interview
        if self.metrics_history:
            avg_fluency    = sum(m.get("fluency_score", 0)      for m in self.metrics_history) / len(self.metrics_history)
            avg_speech_rate= sum(m.get("speech_rate", 0)        for m in self.metrics_history) / len(self.metrics_history)
            avg_pauses     = sum(m.get("pause_count", 0)        for m in self.metrics_history) / len(self.metrics_history)
            avg_fillers    = sum(m.get("filler_count", 0)       for m in self.metrics_history) / len(self.metrics_history)
            avg_grammar    = sum(m.get("grammar_errors", 0)     for m in self.metrics_history) / len(self.metrics_history)
            avg_lexical    = sum(m.get("lexical_diversity", 0)  for m in self.metrics_history) / len(self.metrics_history)
        else:
            avg_fluency = avg_speech_rate = avg_pauses = avg_fillers = avg_grammar = avg_lexical = 0

        if avg_fluency >= 75:
            performance_band = "Strong"
        elif avg_fluency >= 50:
            performance_band = "Moderate"
        else:
            performance_band = "Needs improvement"

        qa_pairs = []
        for i, (q, a) in enumerate(zip(self.questions_asked, self.answers)):
            qa_pairs.append({
                "question_number": i + 1,
                "question": q,
                "answer_preview": a[:200] + "..." if len(a) > 200 else a
            })

        return {
            "session_summary": {
                "job_role":         self.job_role.get("title", "Unknown") if self.job_role else "Unknown",
                "total_questions":  total_questions,
                "total_answers":    total_answers,
                "skills_detected":  self.skills,
                "weak_areas":       self.state.weak_areas,
                "end_reason":       self.end_reason or "manual",
                "performance_band": performance_band
            },
            "fluency_scores": {
                "overall_fluency_score":  round(avg_fluency, 1),
                "avg_speech_rate_wpm":    round(avg_speech_rate, 1),
                "avg_pause_count":        round(avg_pauses, 1),
                "avg_filler_words":       round(avg_fillers, 1),
                "avg_grammar_errors":     round(avg_grammar, 1),
                "avg_lexical_diversity":  round(avg_lexical, 3)
            },
            "feedback": self._generate_feedback(
                avg_fluency, avg_speech_rate, avg_fillers,
                avg_grammar, avg_lexical, avg_pauses
            ),
            "qa_log": qa_pairs
        }


    # ----------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------

    def _get_topic_for_stage(self, stage):
        stage_topics = {
            "skill_validation": self.skills[0] if self.skills else "technical skills",
            "deep_technical":   self.skills[1] if len(self.skills) > 1 else "advanced concepts",
            "scenario":         "problem solving",
            "behavioral":       "communication",
        }
        return stage_topics.get(stage)

    def _generate_feedback(self, fluency, speech_rate, fillers, grammar, lexical, pauses):
        feedback = []

        if fluency >= 75:
            feedback.append("Overall fluency is strong — the candidate communicated clearly and confidently.")
        elif fluency >= 50:
            feedback.append("Fluency is moderate — some areas of communication could be improved.")
        else:
            feedback.append("Fluency needs improvement — practice speaking more clearly and confidently.")

        if speech_rate < 100:
            feedback.append("Speech rate was slow — try to speak at a more natural pace (120–160 WPM).")
        elif speech_rate > 180:
            feedback.append("Speech rate was fast — slow down slightly for better clarity.")
        else:
            feedback.append("Speech rate was natural and easy to follow.")

        if fillers > 5:
            feedback.append("High use of filler words (um, uh, like) — practice pausing instead of filling silence.")
        elif fillers > 2:
            feedback.append("Some filler words detected — minor, but worth reducing.")

        if grammar > 4:
            feedback.append("Several grammar issues detected — review common spoken English patterns.")

        if lexical >= 0.7:
            feedback.append("Excellent vocabulary diversity — responses showed strong command of language.")
        elif lexical >= 0.5:
            feedback.append("Vocabulary diversity is good.")
        else:
            feedback.append("Vocabulary diversity is limited — try to use more varied language in responses.")

        if pauses > 3:
            feedback.append("Frequent long pauses — work on maintaining a steady flow of speech.")

        return feedback