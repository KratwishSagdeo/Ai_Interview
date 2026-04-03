from resume_parser.parser import ResumeParser
from resume_parser.skill_extractor import SkillExtractor
from interview_engine.interview_state import InterviewState
from interview_engine.interview_flow_controller import InterviewFlowController
from interview_engine.difficulty_controller import DifficultyController
from knowledge_engine.topic_graph import TopicGraph
from knowledge_engine.topic_tracker import TopicTracker
from question_engine.followup_generator import FollowUpGenerator
from question_engine.question_generator import QuestionGenerator
from configs.job_roles import get_role
from services.answer_evaluator import AnswerEvaluator
import math
import logging

logger = logging.getLogger("interview_manager")

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

MAX_QUESTIONS             = 15
MIN_QUESTIONS             = 6
WEAK_SCORE_THRESHOLD      = 2
ALLOWED_EXPERIENCE_LEVELS = ["beginner", "intermediate", "expert"]

# Sigmoid termination thresholds
CONFIDENCE_END_THRESHOLD  = 0.80   # Sigmoid output above this → end interview
CONFIDENCE_END_MIN_Q      = 6      # Don't end before this many questions

# Sigmoid shape parameters
SIGMOID_STEEPNESS         = 8      # How sharply the curve rises
SIGMOID_MIDPOINT          = 0.55   # Score at which sigmoid = 0.5


def resolve_job_role(user_role: str, inferred_role: str) -> str:
    if user_role and user_role.strip():
        return user_role.strip()
    return inferred_role


def sigmoid(x: float, k: float = SIGMOID_STEEPNESS, x0: float = SIGMOID_MIDPOINT) -> float:
    """
    Sigmoid function that maps a raw average score (0-1) to a confidence value (0-1).

    - Low scores  (< 0.4) → confidence near 0   → keep asking (candidate struggling)
    - Mid scores  (0.4-0.7) → confidence 0.2-0.8 → continue interview normally
    - High scores (> 0.7) → confidence near 1   → safe to end (candidate is strong)

    The sigmoid prevents ending too early on a lucky answer
    and keeps going when the candidate is borderline.
    """
    try:
        return 1.0 / (1.0 + math.exp(-k * (x - x0)))
    except OverflowError:
        return 0.0 if x < x0 else 1.0


class InterviewManager:

    def __init__(self):

        self.parser = ResumeParser()
        self.skill_extractor = SkillExtractor()
        self.question_generator = QuestionGenerator()
        self.followup_generator = FollowUpGenerator()
        self.answer_evaluator = AnswerEvaluator()
        self.state = InterviewState()
        self.experience_level = "beginner"
        self.flow = InterviewFlowController()
        self.difficulty = DifficultyController()
        self.topic_graph = TopicGraph()
        self.topic_tracker = TopicTracker()

        self.skills: list[str] = []
        self.questions_asked: list[str] = []
        self.answers: list[str] = []
        self.current_question_index = 0
        self.job_role = None
        self.job_role_key = None
        self.resume_context = ""

        self.is_finished = False
        self.end_reason: str = ""

        self.metrics_history: list[dict] = []
        self.evaluation_history: list[float] = []
        self.average_score = 0.0

        # ✅ Sigmoid confidence tracking
        self.confidence = 0.0       # Current sigmoid output
        self.confidence_history: list[float] = []


    # ──────────────────────────────────────────────
    # Start interview
    # ──────────────────────────────────────────────

    def start_interview(self, resume_path, job_role_key="software_engineer", experience_level="beginner", interview_type="full"):

        if experience_level not in ALLOWED_EXPERIENCE_LEVELS:
            experience_level = "beginner"

        self.experience_level = experience_level
        self.state.experience_level = experience_level

        normalized_key = (job_role_key.strip().lower()
                          .replace(" ", "_").replace("-", "_")) if job_role_key else "software_engineer"
        base_role = get_role(normalized_key)
        final_title = resolve_job_role(job_role_key, base_role["title"])
        base_role["title"] = final_title

        self.job_role_key = normalized_key
        self.job_role = base_role

        resume_text = self.parser.extract_text(resume_path)
        self.skills = self.skill_extractor.extract_skills(resume_text)
        self.skills = list(dict.fromkeys(self.job_role.get("focus_skills", []) + self.skills))
        self.resume_context = self.skill_extractor.extract_resume_context(resume_text)

        self.state.skills = self.skills
        self.state.job_role = self.job_role

        logger.info(f"Interview started — role: {final_title}, level: {experience_level}, type: {interview_type}")
        logger.info(f"Skills detected: {self.skills}")
        logger.info(f"Resume context:\n{self.resume_context}")

        # ✅ First question uses stage context from the new flow controller
        return self._generate_stage_question()


    # ──────────────────────────────────────────────
    # Generate stage-appropriate opening question
    # ──────────────────────────────────────────────

    def _generate_stage_question(self):
        """
        Used only for the very first question of each stage
        (when there's no previous answer to follow up on).
        """
        level = self.experience_level
        logger.info(f"Generating question at level: {self.experience_level}")

        stage = self.flow.get_current_stage()
        role_title = self.job_role["title"]

        if stage == "introduction":
            q = (f"Hello! Welcome to your mock interview for the {role_title} role. "
                 f"To start, could you please introduce yourself?")

        elif stage == "resume_deep_dive":
            edu = ""
            for line in self.resume_context.split("\n"):
                if "education" in line.lower() or "b.tech" in line.lower() or "college" in line.lower():
                    edu = line.strip(" -")
                    break
            q = (f"I've had a look at your resume. "
                 f"{'I see you are ' + edu + '. ' if edu else ''}"
                 f"Can you walk me through your background and what led you to pursue {role_title}?")

        elif stage == "projects":
            proj = ""
            for line in self.resume_context.split("\n"):
                if "project" in line.lower() and len(line) > 20:
                    proj = line.strip(" -")[:120]
                    break
            q = (f"I'd love to hear more about your projects. "
                 f"{'Can you tell me about: ' + proj if proj else 'Can you walk me through your most significant project?'}")

        elif stage == "technical":
            top_skill = self.skills[0] if self.skills else "software development"
            if level == "beginner":
                q = f"Let's move into some technical questions. Can you explain your basic understanding and key concepts of {top_skill}?"
            elif level == "intermediate":
                q = f"Let's move into some technical questions. In practical terms, how have you applied your knowledge of {top_skill} in past work?"
            elif level == "expert":
                q = f"Let's move into some technical questions. Can you discuss your experience with scaling and architecture trade-offs involving {top_skill}?"
            else:
                q = f"Let's move into some technical questions. Can you explain your understanding of {top_skill}?"

        elif stage == "hr":
            q = ("Now I'd like to understand you a bit better as a person. "
                 "Can you tell me about a time you faced a difficult challenge and how you handled it?")

        else:
            q = "We're almost done. Do you have any questions for me about the role or the team?"

        self.questions_asked.append(q)
        self.state.add_question(q)
        return q


    # ──────────────────────────────────────────────
    # ✅ Sigmoid-based termination check
    # ──────────────────────────────────────────────

    def _update_confidence(self, new_score: float):
        """
        Recalculates confidence after every answer using sigmoid.

        The sigmoid takes the running average score and outputs
        a confidence value between 0 and 1.

        Confidence is only trusted after MIN_QUESTIONS have been asked
        to avoid ending on lucky early answers.
        """
        self.evaluation_history.append(new_score)
        self.average_score = sum(self.evaluation_history) / len(self.evaluation_history)
        self.confidence = sigmoid(self.average_score)
        self.confidence_history.append(self.confidence)
        logger.info(
            f"Q{len(self.evaluation_history)} score={new_score:.2f} "
            f"avg={self.average_score:.2f} confidence={self.confidence:.3f}"
        )

    def should_end_interview(self):

        n = len(self.questions_asked)
        logger.info(f"Termination check: n={n} avg={self.average_score:.2f} confidence={self.confidence:.3f} threshold={CONFIDENCE_END_THRESHOLD}")

        # Hard cap — always end at MAX_QUESTIONS
        if n >= MAX_QUESTIONS:
            self.end_reason = "max_questions"
            return True

        # Stage completed naturally
        if self.flow.get_current_stage() == "closing" and n >= MIN_QUESTIONS:
            self.end_reason = "all_stages_done"
            return True

        if n >= 6 and self.average_score <= 0.30:
            self.end_reason = "weak_candidate"
            logger.info("Weak candidate detected — ending interview early")
            return True

        # ✅ Sigmoid confidence threshold
        # Only fires after CONFIDENCE_END_MIN_Q questions
        # and only when confidence is consistently high
        if (n >= CONFIDENCE_END_MIN_Q
                and len(self.confidence_history) >= CONFIDENCE_END_MIN_Q):

            # Use average of last 3 confidence values for stability
            recent_conf = self.confidence_history[-3:]
            avg_recent_conf = sum(recent_conf) / len(recent_conf)

            if avg_recent_conf >= CONFIDENCE_END_THRESHOLD:
                self.end_reason = "confidence_threshold_met"
                logger.info(f"Sigmoid confidence {avg_recent_conf:.3f} exceeded threshold — ending interview")
                return True

        return False


    # ──────────────────────────────────────────────
    # Process answer
    # ──────────────────────────────────────────────

    def process_answer(self, answer, fluency_metrics=None):
        """
        Returns:
          { "type": "question", "content": "...", "evaluation": {...}, "confidence": float }
          { "type": "end",      "content": "...", "evaluation": {...}, "confidence": float }
        """

        self.answers.append(answer)
        self.state.add_answer(answer)

        question = self.questions_asked[self.current_question_index]

        # ✅ Evaluate answer content
        evaluation = self.answer_evaluator.evaluate(
            question=question,
            answer=answer,
            previous_answers=self.answers[:-1],
            session_avg=self.average_score if self.average_score > 0 else 0.5
        )

        level = self.experience_level
        base_score = evaluation.get("final_score", evaluation.get("score", 0.5))
        logger.info(f"Evaluation dict keys: {list(evaluation.keys())} | base_score={base_score}")

        if level == "beginner":
            adjusted_score = min(1.0, base_score + 0.1)
        elif level == "intermediate":
            adjusted_score = base_score
        elif level == "expert":
            adjusted_score = max(0.0, base_score - 0.1)
        else:
            adjusted_score = base_score

        evaluation["adjusted_score"] = round(adjusted_score, 3)
        evaluation["experience_level"] = level

        logger.info(f"Level: {level} | Base: {base_score:.2f} → Adjusted: {adjusted_score:.2f}")

        # ✅ Update sigmoid confidence
        self._update_confidence(evaluation["adjusted_score"])

        # Fluency weak area detection
        if fluency_metrics:
            self.metrics_history.append(fluency_metrics)
            fillers = fluency_metrics.get("filler_count", 0)
            grammar = fluency_metrics.get("grammar_errors", 0)
            if fillers + grammar > WEAK_SCORE_THRESHOLD:
                weak = self._get_topic_for_stage(self.flow.get_current_stage())
                if weak:
                    self.state.add_weak_area(weak)

        # Content weak area detection
        if evaluation["adjusted_score"] < 0.4:
            weak = self._get_topic_for_stage(self.flow.get_current_stage())
            if weak and weak not in self.state.weak_areas:
                self.state.add_weak_area(weak)

        self.current_question_index += 1
        self.flow.increment_stage_count()

        # ✅ Advance stage when budget is spent
        if self.flow.should_advance_stage():
            next_stage = self.flow.next_stage()
            logger.info(f"Stage → {next_stage}")

        # ✅ Check termination
        if self.should_end_interview():
            self.is_finished = True

            # If ending naturally at closing stage — ask a final warm closing question
            if self.end_reason in ("confidence_threshold_met", "all_stages_done"):
                closing = (
                    f"You've done really well in this interview. "
                    f"Based on what we've covered today, I think you have a strong foundation in "
                    f"{', '.join(self.skills[:3])}. "
                    f"Do you have any final questions for me before we wrap up?"
                )
                self.questions_asked.append(closing)
                self.state.add_question(closing)
                return {
                    "type": "end",
                    "content": closing,
                    "evaluation": evaluation,
                    "confidence": round(self.confidence, 3)
                }

            return {
                "type": "end",
                "content": "Thank you for your time. That concludes our interview. You will receive your detailed feedback shortly.",
                "evaluation": evaluation,
                "confidence": round(self.confidence, 3)
            }

        # ✅ Get stage context for follow-up generation
        stage_context = self.flow.get_stage_prompt_context(
            self.job_role["title"],
            self.skills,
            self.resume_context
        )

        # Generate follow-up question
        followup = self.followup_generator.generate_followup(
            question=question,
            answer=answer,
            skills=self.skills,
            previous_questions=self.questions_asked,
            job_role=self.job_role,
            weak_areas=self.state.weak_areas,
            resume_context=self.resume_context,
            stage_context=stage_context,         # ✅ stage-aware prompt
            experience_level=self.experience_level
        )

        self.questions_asked.append(followup)
        self.state.add_question(followup)

        return {
            "type": "question",
            "content": followup,
            "evaluation": evaluation,
            "confidence": round(self.confidence, 3)
        }


    # ──────────────────────────────────────────────
    # Final report
    # ──────────────────────────────────────────────

    def generate_report(self):

        if self.metrics_history:
            avg_fluency     = sum(m.get("fluency_score", 0)     for m in self.metrics_history) / len(self.metrics_history)
            avg_speech_rate = sum(m.get("speech_rate", 0)       for m in self.metrics_history) / len(self.metrics_history)
            avg_pauses      = sum(m.get("pause_count", 0)       for m in self.metrics_history) / len(self.metrics_history)
            avg_fillers     = sum(m.get("filler_count", 0)      for m in self.metrics_history) / len(self.metrics_history)
            avg_grammar     = sum(m.get("grammar_errors", 0)    for m in self.metrics_history) / len(self.metrics_history)
            avg_lexical     = sum(m.get("lexical_diversity", 0) for m in self.metrics_history) / len(self.metrics_history)
        else:
            avg_fluency = avg_speech_rate = avg_pauses = avg_fillers = avg_grammar = avg_lexical = 0

        avg_content = round(self.average_score, 3)
        fluency_norm = avg_fluency / 100.0
        overall = round(0.6 * avg_content + 0.4 * fluency_norm, 3)

        if overall >= 0.75:
            band = "Strong"
        elif overall >= 0.5:
            band = "Moderate"
        else:
            band = "Needs improvement"

        qa_pairs = [
            {
                "question_number": i + 1,
                "question": q,
                "answer_preview": a[:200] + "..." if len(a) > 200 else a
            }
            for i, (q, a) in enumerate(zip(self.questions_asked, self.answers))
        ]

        return {
            "session_summary": {
                "job_role":         self.job_role.get("title", "Unknown") if self.job_role else "Unknown",
                "total_questions":  len(self.questions_asked),
                "total_answers":    len(self.answers),
                "skills_detected":  self.skills,
                "weak_areas":       self.state.weak_areas,
                "end_reason":       self.end_reason or "manual",
                "performance_band": band,
                "overall_score":    overall,
                "final_confidence": round(self.confidence, 3)
            },
            "content_scores": {
                "average_content_score": avg_content,
                "total_evaluated":       len(self.evaluation_history),
                "confidence_history":    [round(c, 3) for c in self.confidence_history]
            },
            "fluency_scores": {
                "overall_fluency_score":  round(avg_fluency, 1),
                "avg_speech_rate_wpm":    round(avg_speech_rate, 1),
                "avg_pause_count":        round(avg_pauses, 1),
                "avg_filler_words":       round(avg_fillers, 1),
                "avg_grammar_errors":     round(avg_grammar, 1),
                "avg_lexical_diversity":  round(avg_lexical, 3)
            },
            "feedback": self._generate_feedback(avg_content, avg_fluency, avg_speech_rate,
                                                 avg_fillers, avg_grammar, avg_lexical, avg_pauses),
            "qa_log": qa_pairs
        }


    def _get_topic_for_stage(self, stage):
        return {
            "resume_deep_dive": "resume background",
            "projects":         self.skills[0] if self.skills else "projects",
            "technical":        self.skills[1] if len(self.skills) > 1 else "technical skills",
            "hr":               "communication",
        }.get(stage)

    def _generate_feedback(self, content, fluency, rate, fillers, grammar, lexical, pauses):
        fb = []

        if content >= 0.75:
            fb.append("Strong technical knowledge — answers were accurate, detailed and well-reasoned.")
        elif content >= 0.4:
            fb.append("Moderate technical knowledge — some answers lacked depth or had minor inaccuracies.")
        else:
            fb.append("Technical knowledge needs improvement — practice explaining concepts clearly.")

        if fluency >= 75:
            fb.append("Communication is strong — spoke clearly and confidently.")
        elif fluency >= 50:
            fb.append("Communication is moderate — work on structuring answers more clearly.")
        else:
            fb.append("Communication needs improvement — practice speaking at a steady pace.")

        if rate < 100:
            fb.append("Speech was slow — aim for 120–160 WPM.")
        elif rate > 180:
            fb.append("Speech was fast — slow down for clarity.")

        if fillers > 5:
            fb.append("High filler word usage — practice pausing instead of saying 'um' or 'uh'.")
        elif fillers > 2:
            fb.append("Some filler words detected — minor but worth reducing.")

        if lexical >= 0.7:
            fb.append("Excellent vocabulary diversity.")
        elif lexical < 0.5:
            fb.append("Vocabulary diversity is limited — use more varied language in answers.")

        if pauses > 3:
            fb.append("Frequent long pauses — work on maintaining a steady flow.")

        return fb