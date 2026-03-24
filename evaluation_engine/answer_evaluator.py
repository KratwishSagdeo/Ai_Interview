import json
import logging
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger("answer_evaluator")

class EvaluationResult(BaseModel):
    correctness: float = Field(default=0.5)
    depth: float = Field(default=0.5)
    clarity: float = Field(default=0.5)
    consistency: float = Field(default=0.5)
    final_score: float = Field(default=0.5)
    reasoning: str = Field(default="No reasoning provided")
    confidence_level: str = Field(default="medium")

def sanitize_score(value):
    try:
        val = float(value)
        return max(0.0, min(1.0, val))
    except:
        return 0.5

class AnswerEvaluator:

    def __init__(self):
        self.client = OpenAI()

    def evaluate(self, question, answer, previous_answers=None, session_avg=0.5):
        system_prompt = """You are an expert AI technical interviewer responsible for evaluating candidate answers in a precise, consistent, and objective manner.

You MUST strictly follow the evaluation rules and output format. Your output will be consumed by an automated backend system.

---

## EVALUATION DIMENSIONS (0 to 1 SCALE)

Score the answer across the following four dimensions:

1. correctness
* 1.0 → Completely correct, no factual errors
* 0.7 → Mostly correct, minor mistakes
* 0.4 → Partially correct, major gaps
* 0.0 → Incorrect or irrelevant

2. depth
* 1.0 → Includes reasoning, examples, edge cases
* 0.7 → Some explanation, limited depth
* 0.4 → Superficial explanation
* 0.0 → No explanation

3. clarity
* 1.0 → Well-structured, clear, easy to follow
* 0.7 → Understandable but not well-structured
* 0.4 → Hard to follow
* 0.0 → Confusing or incoherent

4. consistency
* Compare with previous answers if provided
* 1.0 → Fully consistent with prior responses
* 0.7 → Minor inconsistencies
* 0.4 → Noticeable contradictions
* 0.0 → Direct contradiction
* If no previous answers exist → return 0.5

---

## SCORING RULES (CRITICAL)

* All scores MUST be between 0.0 and 1.0
* Use increments of 0.1 or 0.05 only
* Avoid random precision (e.g., 0.873 is NOT allowed)

---

## PENALTY RULES

Apply strict penalties in these cases:

* If the answer is vague → reduce depth and clarity
* If the answer is verbose but incorrect → reduce correctness heavily
* If the answer avoids the question → correctness <= 0.3
* If the answer contradicts itself → reduce clarity and consistency

---

## FINAL SCORE

Compute:
final_score = 
0.4 * correctness + 
0.3 * depth + 
0.2 * clarity + 
0.1 * consistency

---

## CONFIDENCE LEVEL

* high → final_score >= 0.75
* medium → 0.4 <= final_score < 0.75
* low → final_score < 0.4

---

## REASONING

Provide a short explanation (max 2 lines) explaining why the score was assigned.

---

## STRICT OUTPUT FORMAT (JSON ONLY)

Return ONLY valid JSON. Do not include any extra text.

{
"correctness": number,
"depth": number,
"clarity": number,
"consistency": number,
"final_score": number,
"confidence_level": "low | medium | high",
"reasoning": "string"
}

---

## INPUT YOU WILL RECEIVE

* question: the interview question
* candidate_answer: the candidate's response
* previous_answers: optional list of past answers

Use previous_answers ONLY for evaluating consistency.

---

## BEHAVIORAL CONSTRAINTS

* Be strict but fair
* Do not guess missing information
* Do not reward verbosity without correctness
* Do not inflate scores
* Be consistent across evaluations

---

## GOAL

Your evaluation directly impacts interview progression logic, so consistency and reliability are critical."""

        user_content = f"question:\n{question}\n\ncandidate_answer:\n{answer}\n"
        if previous_answers:
            # FIX: Only use the last 2 answers to prevent token explosion and noise
            recent_answers = previous_answers[-2:]
            formatted_prev = "\n".join(f"- {a}" for a in recent_answers)
            user_content += f"\nprevious_answers (last 2 only):\n{formatted_prev}\n"

        fallback_payload = {
            "correctness": session_avg,
            "depth": session_avg,
            "clarity": session_avg,
            "consistency": session_avg,
            "final_score": session_avg,
            "reasoning": "Evaluation error occurred. Using session average.",
            "confidence_level": "high" if session_avg >= 0.75 else "medium" if session_avg >= 0.4 else "low"
        }

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content
            data = json.loads(result_text)
            
            # FIX: Pydantic Validation ensures structure won't break
            eval_obj = EvaluationResult(**data)
            validated_data = eval_obj.model_dump() if hasattr(eval_obj, "model_dump") else eval_obj.dict()

            # FIX: Sanitize outputs (LLMs aren't strict validators)
            corr = sanitize_score(validated_data.get("correctness"))
            dep = sanitize_score(validated_data.get("depth"))
            clar = sanitize_score(validated_data.get("clarity"))
            cons = sanitize_score(validated_data.get("consistency"))
            
            validated_data["correctness"] = corr
            validated_data["depth"] = dep
            validated_data["clarity"] = clar
            validated_data["consistency"] = cons

            # FIX: Manually compute final_score to prevent manipulation/hallucination
            computed_score = round(0.4 * corr + 0.3 * dep + 0.2 * clar + 0.1 * cons, 4)
            validated_data["final_score"] = computed_score

            # Re-map confidence level strictly based on computed score
            if computed_score >= 0.75:
                validated_data["confidence_level"] = "high"
            elif computed_score >= 0.4:
                validated_data["confidence_level"] = "medium"
            else:
                validated_data["confidence_level"] = "low"

            return validated_data

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return fallback_payload