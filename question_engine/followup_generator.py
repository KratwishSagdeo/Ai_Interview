import os
import time
import requests
import logging

logger = logging.getLogger("followup_generator")


class FollowUpGenerator:

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        self.url = "https://api.groq.com/openai/v1/chat/completions"


    def generate_followup(
        self,
        question,
        answer,
        skills=None,
        previous_questions=None,
        job_role=None,
        weak_areas=None          # ✅ P2: weak area awareness
    ):

        try:
            start_time = time.time()
            answer = answer[:500]

            # ✅ P2: Role context
            role_context = ""
            if job_role:
                role_title = job_role.get("title", "Software Engineer")
                key_topics = ", ".join(job_role.get("key_topics", []))
                role_context = f"The candidate is interviewing for: {role_title}\nKey topics for this role: {key_topics}\n"

            # ✅ P2: Deduplication — pass last 5 questions to avoid repeats
            dedup_context = ""
            if previous_questions:
                recent = previous_questions[-5:]
                formatted = "\n".join(f"- {q}" for q in recent)
                dedup_context = f"\nQuestions already asked (DO NOT repeat or closely paraphrase these):\n{formatted}\n"

            # ✅ P2: Weak area context — push harder on struggling topics
            weak_context = ""
            if weak_areas:
                formatted_weak = ", ".join(weak_areas)
                weak_context = f"\nThe candidate struggled with: {formatted_weak}. If the answer touches on these, ask a deeper probing question.\n"

            prompt = f"""You are a strict technical interviewer.
{role_context}{dedup_context}{weak_context}
Ask 1 short follow-up interview question based on the candidate's answer below.

Rules:
- Focus on ONE concept from the answer
- Keep it relevant to the job role
- Max 15 words
- Must be different from all questions already asked above
- Return ONLY the question ending with '?'

Q: {question}
A: {answer}
"""

            logger.info("Calling Groq for follow-up question")

            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 50,
                "temperature": 0.7,
                "top_p": 0.9
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(self.url, json=payload, headers=headers)
            data = response.json()

            if "error" in data:
                error = data["error"]
                code = error.get("code", "")
                if response.status_code == 429 or code == "rate_limit_exceeded":
                    logger.warning("Groq quota exceeded (429)")
                    return "Can you elaborate on that concept in more detail?"
                raise Exception(error.get("message", "Unknown Groq error"))

            followup = data["choices"][0]["message"]["content"].strip()

            if len(followup.split()) < 3:
                raise Exception(f"Bad output: {followup}")

            if not followup.endswith("?"):
                followup = followup + "?"

            elapsed = time.time() - start_time
            logger.info(f"Groq follow-up generated in {elapsed:.2f}s: {followup}")

            return followup

        except Exception as e:
            logger.error(f"Groq FAILED: {e}")
            return "Can you explain that in more detail?"