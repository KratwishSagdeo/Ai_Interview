import os
import json
import requests
import logging

logger = logging.getLogger("semantic_validator")

from services.ai_provider.groq_client import GroqClientProvider

def _call_groq(prompt: str) -> str:
    """Internal Groq call — always used, no fallback to None."""
    provider = GroqClientProvider()
    client = provider.get_client()

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80,
        temperature=0.0    # deterministic — this is a classifier not a generator
    )
    return response.choices[0].message.content.strip()


def is_relevant_answer(question: str, answer: str, llm_call=None) -> dict:
    """
    Always calls Groq LLM to classify the answer.
    Returns:
      { "verdict": "RELEVANT" | "PARTIALLY_RELEVANT" | "IRRELEVANT", "reason": "..." }

    IRRELEVANT → caller must stop the interview immediately and generate report.
    """

    answer = answer.strip()

    # Empty answer — instant irrelevant
    if len(answer) == 0:
        return {"verdict": "IRRELEVANT", "reason": "Empty answer — candidate said nothing."}

    # Too short to be meaningful (less than 3 words)
    if len(answer.split()) < 3:
        return {"verdict": "IRRELEVANT", "reason": "Answer too short to be meaningful."}

    prompt = f"""You are a professional technical interviewer evaluating a candidate's response during a mock interview.

Your ONLY job is to classify whether the candidate's answer is relevant to the question asked.

Classify into exactly ONE of:

RELEVANT
- Answer directly addresses the question
- May be imperfect, short, or have minor errors — still RELEVANT if on-topic

PARTIALLY_RELEVANT
- Answer is somewhat related but incomplete, vague, or slightly off-topic
- Still shows some genuine attempt to answer

IRRELEVANT
- Answer is completely unrelated to the question
- Random words, nonsense, gibberish, personal rants, abusive content
- Clearly does not attempt to answer the question at all
- Examples: saying their name repeatedly, quoting movies, typing random characters

RULES:
- Do NOT reject short answers — shortness alone is not irrelevance
- Do NOT expect perfect technical wording
- If there is ANY genuine attempt to answer → PARTIALLY_RELEVANT at minimum
- Only use IRRELEVANT when the answer has absolutely no connection to the question

Question: {question}
Answer: {answer}

Respond ONLY with valid JSON, no extra text:
{{"verdict": "RELEVANT" or "PARTIALLY_RELEVANT" or "IRRELEVANT", "reason": "one sentence explanation"}}"""

    try:
        raw = _call_groq(prompt)

        # Strip markdown code fences if present
        raw = raw.replace("```json", "").replace("```", "").strip()

        data = json.loads(raw)
        verdict = data.get("verdict", "RELEVANT").strip().upper()

        if verdict not in ("RELEVANT", "PARTIALLY_RELEVANT", "IRRELEVANT"):
            verdict = "RELEVANT"

        logger.info(f"Validation verdict: {verdict} — {data.get('reason', '')}")
        return {"verdict": verdict, "reason": data.get("reason", "")}

    except Exception as e:
        # If LLM call fails, default to RELEVANT so interview doesn't
        # accidentally stop due to a network error
        logger.error(f"Validation LLM call failed: {e} — defaulting to RELEVANT")
        return {"verdict": "RELEVANT", "reason": "Validation unavailable — defaulting to relevant."}