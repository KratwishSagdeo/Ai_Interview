class InterviewFlowController:

    def __init__(self):

        self.stages = [
            "introduction",
            "resume_deep_dive",
            "projects",
            "technical",
            "hr",
            "closing",
        ]

        self.current_stage_index = 0

        # ✅ Question budget per stage
        # Technical gets the most questions — it's the core of the interview
        self.stage_question_budget = {
            "introduction":    1,
            "resume_deep_dive":2,
            "projects":        3,
            "technical":       4,
            "hr":              2,
            "closing":         1,
        }

        self.questions_in_current_stage = 0

    def get_current_stage(self):
        return self.stages[self.current_stage_index]

    def next_stage(self):
        if self.current_stage_index < len(self.stages) - 1:
            self.current_stage_index += 1
            self.questions_in_current_stage = 0
        return self.get_current_stage()

    def increment_stage_count(self):
        self.questions_in_current_stage += 1

    def should_advance_stage(self):
        stage  = self.get_current_stage()
        budget = self.stage_question_budget.get(stage, 2)
        return self.questions_in_current_stage >= budget

    def get_stage_prompt_context(self, role_title, skills, resume_context):
        """
        Returns a stage context string injected into the LLM prompt.
        Critically — the stage NAME is always included so followup_generator
        can detect which stage we're in reliably.
        """
        stage      = self.get_current_stage()
        top_skills = ", ".join(skills[:4]) if skills else "their listed skills"

        # ✅ Each context string starts with "STAGE: <name>" so the
        # followup_generator can always detect the current stage reliably
        contexts = {
            "introduction": (
                f"STAGE: introduction\n"
                f"You are starting the interview for the {role_title} role. "
                f"The candidate has just introduced themselves. "
                f"Ask a natural warm follow-up about their background or motivation — "
                f"make them feel at ease."
            ),
            "resume_deep_dive": (
                f"STAGE: resume_deep_dive\n"
                f"You are reviewing the candidate's resume for the {role_title} role. "
                f"Their background: {resume_context[:250] if resume_context else 'see resume'}. "
                f"Pick ONE specific item — a degree, internship, project, or listed skill — "
                f"and ask a targeted question about it. Do not ask generic questions."
            ),
            "projects": (
                f"STAGE: projects\n"
                f"You are doing a deep dive into the candidate's projects. "
                f"Project details: {resume_context[250:500] if resume_context else 'see resume'}. "
                f"Ask about HOW they built it, WHAT decisions they made, WHAT went wrong, "
                f"and what the impact was. Push for specifics, not summaries."
            ),
            "technical": (
    f"STAGE: technical\n"
    f"You are conducting an interview for {role_title}.\n"
    f"STRICT RULE: Only ask questions related to {role_title}.\n"
    f"Ignore unrelated resume domains completely.\n"
    f"Focus on these skills: {top_skills}.\n"
    f"Do NOT ask questions outside this role.\n"
),
            "hr": (
                f"STAGE: hr\n"
                f"You are in the behavioural/HR round for the {role_title} role. "
                f"Ask a situational question using the STAR format — "
                f"about a real situation the candidate faced, the action they took, "
                f"and the result they achieved. Focus on: teamwork, handling pressure, "
                f"conflict resolution, or leadership."
            ),
            "closing": (
                f"STAGE: closing\n"
                f"The interview is wrapping up. "
                f"Invite the candidate to ask any questions they have about the {role_title} role, "
                f"the team, the tech stack, or the company culture. "
                f"Keep it warm and conversational."
            ),
        }

        return contexts.get(stage, f"STAGE: {stage}\nContinue the {role_title} interview naturally.")