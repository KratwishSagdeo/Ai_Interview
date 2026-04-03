import os
import time
import requests
import logging

logger = logging.getLogger("followup_generator")

# ──────────────────────────────────────────────────────────────
# Difficulty level definitions
# Concrete rules injected into the prompt — not vague labels
# ──────────────────────────────────────────────────────────────

LEVEL_CONFIGS = {
    "beginner": {
        "label": "Entry-level / Fresher",
        "rules": """- Ask about basic definitions and fundamental concepts ONLY
- Use simple language — avoid jargon and acronyms without explanation
- Questions must be answerable by someone who has studied but has little/no work experience
- Appropriate: "What is X?", "How does X work?", "Why do we use X?"
- NOT appropriate: system design, scalability, architecture trade-offs, production issues
- Keep it encouraging and non-intimidating""",
        "temperature": 0.6,
    },
    "intermediate": {
        "label": "1–3 years experience",
        "rules": """- Ask scenario-based and applied questions that require real project experience
- Candidate should explain HOW they used X, not just WHAT X is
- Appropriate: "How did you handle X in your project?", "What challenges did you face with X?", "How did you debug Y?"
- Can ask about common patterns and moderate-level trade-offs
- Avoid pure definitions (too easy) and avoid deep architecture (too hard)
- Push for specifics — don't accept vague answers""",
        "temperature": 0.7,
    },
    "expert": {
        "label": "Senior / 5+ years experience",
        "rules": """- Ask deep technical, architectural, and system design questions
- Expect discussion of trade-offs, edge cases, and design rationale
- Appropriate: scalability, performance optimisation, security design, distributed systems
- Push back with: "Why that approach over X?", "What are the failure modes?", "How would you scale this to 10x?"
- Expect specific numbers, real-world constraints, and lessons learned
- Be challenging — this candidate should be battle-tested""",
        "temperature": 0.8,
    }
}

# ──────────────────────────────────────────────────────────────
# Stage-specific focus instructions
# These anchor the question to the correct interview phase
# ──────────────────────────────────────────────────────────────

STAGE_FOCUS = {
    "introduction":    "Ask a natural follow-up about their background, motivation, or career goals. Be warm and conversational.",
    "resume_deep_dive": "Pick ONE specific thing from their resume (degree, internship, skill, or company) and ask about it directly. Be specific — not generic.",
    "projects":        "Dig deeper into the project they described. Ask about technical decisions made, challenges faced, what they'd do differently, or the measurable impact.",
    "technical":       "Test deeper technical understanding. Ask about edge cases, how something works under the hood, or a practical application of the concept they explained.",
    "hr":              "Ask a behavioural question in STAR format — about a real Situation, what Action they took, and what the Result was. Focus on teamwork, conflict, or pressure.",
    "closing":         "Ask if they have questions about the role, team culture, tech stack, or growth opportunities at the company.",
}


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
        weak_areas=None,
        resume_context=None,
        stage_context=None,
        experience_level="beginner"
    ):

        try:
            start_time = time.time()
            answer = answer[:600]

            role_title = job_role.get("title", "Software Engineer") if job_role else "Software Engineer"

            # ── Resolve level ─────────────────────────────────────
            level = experience_level if experience_level in LEVEL_CONFIGS else "beginner"
            lvl   = LEVEL_CONFIGS[level]

            # ── Detect current stage from stage_context string ────
            current_stage = "technical"
            if stage_context:
                for s in STAGE_FOCUS:
                    if s.replace("_", " ") in stage_context.lower() or s in stage_context.lower():
                        current_stage = s
                        break

            stage_focus = STAGE_FOCUS.get(current_stage, "Continue the interview naturally.")

            # ── Resume context ────────────────────────────────────
            resume_section = ""
            if resume_context and resume_context.strip():
                resume_section = (
                    f"\nCANDIDATE BACKGROUND (from resume):\n"
                    f"{resume_context[:700]}\n"
                    f"Use this to make questions specific to their actual experience.\n"
                )

            # ── Deduplication ─────────────────────────────────────
            dedup = ""
            if previous_questions:
                recent = previous_questions[-6:]
                dedup = (
                    "\nQUESTIONS ALREADY ASKED — do NOT repeat or rephrase these:\n"
                    + "\n".join(f"  • {q}" for q in recent) + "\n"
                )

            # ── Weak areas ────────────────────────────────────────
            weak = ""
            if weak_areas:
                weak = (
                    f"\nWEAK AREAS DETECTED: {', '.join(weak_areas)}. "
                    f"If the answer relates to these, probe deeper.\n"
                )

            # ── Final prompt ──────────────────────────────────────
            prompt = f"""You are a professional interviewer conducting a mock interview for a {role_title} role.

=== CANDIDATE LEVEL: {lvl['label'].upper()} ===
DIFFICULTY RULES (apply these strictly to every question you generate):
{lvl['rules']}

=== CURRENT STAGE: {current_stage.upper().replace('_', ' ')} ===
WHAT TO FOCUS ON: {stage_focus}
{resume_section}{dedup}{weak}
=== CANDIDATE'S LATEST ANSWER (context only — use to guide depth, not topic) ===
Question asked: {question}
Candidate answered: {answer}

=== YOUR TASK ===
Generate exactly ONE follow-up question that:
1. Strictly follows the difficulty rules for {level} level
2. Is appropriate for the {current_stage.replace('_', ' ')} stage
3. Builds directly on what the candidate just said
4. PRIORITY: Reference the candidate's actual projects, internships, and skills from their resume.
   Ask about specific things they built, specific technologies they used, specific challenges they faced.
   Do NOT ask generic questions that could apply to any candidate.
5. Has NOT been asked before

OUTPUT: Return ONLY the question. No preamble. No explanation. End with '?'. Max 20 words."""

            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 80,
                "temperature": lvl["temperature"],
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
                if response.status_code == 429 or error.get("code") == "rate_limit_exceeded":
                    logger.warning("Groq quota exceeded")
                    return "Can you elaborate on that in more detail?"
                raise Exception(error.get("message", "Unknown Groq error"))

            followup = data["choices"][0]["message"]["content"].strip()

            # Strip any preamble the model accidentally adds
            for prefix in ["question:", "follow-up:", "next question:", "q:", "interviewer:"]:
                if followup.lower().startswith(prefix):
                    followup = followup[len(prefix):].strip()

            if len(followup.split()) < 3:
                raise Exception(f"Bad output: {followup}")

            if not followup.endswith("?"):
                followup = followup + "?"

            logger.info(f"[{level}][{current_stage}] {time.time() - start_time:.2f}s → {followup}")
            return followup

        except Exception as e:
            logger.error(f"Groq FAILED: {e}")
            return "Can you explain that in more detail?"