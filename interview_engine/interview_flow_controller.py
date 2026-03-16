# ----------------------------------------------------
# InterviewFlowController
# ----------------------------------------------------

# This class controls the stages of the interview
class InterviewFlowController:


    # ----------------------------------------------------
    # Constructor
    # ----------------------------------------------------

    def __init__(self):

        # Define interview stages
        self.stages = [

            "introduction",
            "resume_discussion",
            "skill_validation",
            "deep_technical",
            "scenario",
            "behavioral",
            "closing"
        ]

        # Track current stage
        self.current_stage_index = 0


    # ----------------------------------------------------
    # Get current stage
    # ----------------------------------------------------

    def get_current_stage(self):

        return self.stages[self.current_stage_index]


    # ----------------------------------------------------
    # Move to next stage
    # ----------------------------------------------------

    def next_stage(self):

        if self.current_stage_index < len(self.stages) - 1:

            self.current_stage_index += 1

        return self.get_current_stage()