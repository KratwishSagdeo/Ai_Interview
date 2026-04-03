import json
import logging
from pydantic import BaseModel, Field
from services.ai_provider.groq_client import GroqClientProvider

logger = logging.getLogger("answer_evaluator")


class EvaluationResult(BaseModel):
    correctness:  float = Field(default=0.5)
    depth:        float = Field(default=0.5)
    clarity:      float = Field(default=0.5)
    consistency:  float = Field(default=0.5)
    final_score:  float = Field(default=0.5)
    confidence_level: str = Field(default="medium")
    reasoning:    str = Field(default="No reasoning provided.")


def sanitize_score(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (ValueError, TypeError):
        return 0.5


class AnswerEvaluator:

    def __init__(self):
        self.provider = GroqClientProvider()
        self.client   = self.provider.get_client()

    def evaluate(self, question, answer, previous_answers=None, session_avg=0.5):

        system_prompt = """You are a strict but fair technical interviewer evaluating a candidate's answer.

Evaluate on FOUR dimensions (0.0 to 1.0 scale):

correctness  — Is the answer factually accurate?
  1.0 = completely correct
  0.7 = mostly correct, minor errors
  0.4 = partially correct, notable gaps
  0.0 = wrong or irrelevant

depth        — Does the answer show understanding beyond surface level?
  1.0 = detailed reasoning, examples, edge cases
  0.7 = some explanation
  0.4 = superficial
  0.0 = no explanation

clarity      — Is the answer well-structured and easy to follow?
  1.0 = clear, organised, concise
  0.7 = understandable but could be better structured
  0.4 = hard to follow
  0.0 = incoherent

consistency  — Does it align with previous answers? (0.5 if no prior answers)
  1.0 = fully consistent
  0.7 = minor inconsistency
  0.4 = noticeable contradiction
  0.0 = direct contradiction

SCORING RULES:
- Use only increments of 0.05 or 0.1
- Do NOT inflate scores
- Do NOT penalise for brevity alone — a short correct answer is still correct
- final_score = 0.4*correctness + 0.3*depth + 0.2*clarity + 0.1*consistency
- confidence_level: "high" if final_score >= 0.75, "medium" if >= 0.4, else "low"

Return ONLY valid JSON, no extra text:
{
  "correctness": float,
  "depth": float,
  "clarity": float,
  "consistency": float,
  "final_score": float,
  "confidence_level": "low|medium|high",
  "reasoning": "one sentence explanation"
}"""

        user_content = f"question:\n{question}\n\ncandidate_answer:\n{answer}\n"
        if previous_answers:
            recent = previous_answers[-2:]
            user_content += "\nprevious_answers (last 2):\n" + "\n".join(f"- {a}" for a in recent) + "\n"

        fallback = {
            "correctness":     session_avg,
            "depth":           session_avg,
            "clarity":         session_avg,
            "consistency":     session_avg,
            "final_score":     session_avg,
            "confidence_level": "medium" if session_avg >= 0.4 else "low",
            "reasoning":       "Evaluation unavailable — using session average."
        }

        try:
            response = self.client.chat.completions.create(
                model=self.provider.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_content}
                ],
                temperature=0.1
            )

            data = json.loads(response.choices[0].message.content)
            ev   = EvaluationResult(**data)
            out  = ev.model_dump()

            # Sanitize all scores
            for key in ("correctness", "depth", "clarity", "consistency"):
                out[key] = sanitize_score(out[key])

            # Always recompute final_score — never trust LLM's calculation
            out["final_score"] = round(
                0.4 * out["correctness"] +
                0.3 * out["depth"]       +
                0.2 * out["clarity"]     +
                0.1 * out["consistency"],
                4
            )

            # Recompute confidence level from actual score
            fs = out["final_score"]
            out["confidence_level"] = "high" if fs >= 0.75 else "medium" if fs >= 0.4 else "low"

            logger.info(f"Evaluation: score={out['final_score']} confidence={out['confidence_level']}")
            return out

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return fallback