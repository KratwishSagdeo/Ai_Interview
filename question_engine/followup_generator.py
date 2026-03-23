import os
import time
import requests


class FollowUpGenerator:

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")

        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")

        self.url = "https://api.groq.com/openai/v1/chat/completions"


    def generate_followup(self, question, answer, skills=None, previous_questions=None, job_role=None):

        try:
            start_time = time.time()

            answer = answer[:500]

            # ✅ Build role context string if role is provided
            role_context = ""
            if job_role:
                role_title = job_role.get("title", "Software Engineer")
                key_topics = ", ".join(job_role.get("key_topics", []))
                role_context = f"""
The candidate is interviewing for: {role_title}
Key topics for this role: {key_topics}
Keep your follow-up question relevant to this role.
"""

            prompt = f"""You are a technical interviewer.
{role_context}
Ask 1 short follow-up interview question based on the candidate's answer below.

Rules:
- Focus on ONE concept from the answer
- Keep it relevant to the job role above
- Max 15 words
- Return ONLY the question ending with '?'

Q: {question}
A: {answer}
"""

            print("🔥 Calling Groq via REST...")

            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
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

            print("🧠 Groq Raw:", data)

            if "error" in data:
                error = data["error"]
                code = error.get("code", "")
                if response.status_code == 429 or code == "rate_limit_exceeded":
                    print(f"⚠️ Groq quota exceeded (429): {error.get('message', 'Limit reached')}")
                    return "Can you elaborate on that concept in more detail?"
                raise Exception(error.get("message", "Unknown Groq error"))

            followup = data["choices"][0]["message"]["content"].strip()

            # ✅ Simple validation — just check it has enough words
            if len(followup.split()) < 3:
                raise Exception(f"Bad output: {followup}")

            # ✅ Ensure it ends with ? (add one if missing)
            if not followup.endswith("?"):
                followup = followup + "?"

            elapsed = time.time() - start_time
            print(f"✅ Groq Output: {followup}")
            print(f"⏱ Groq Time: {elapsed:.2f}s")

            return followup

        except Exception as e:
            print("❌ Groq FAILED:", e)
            return "Can you explain that in more detail?"