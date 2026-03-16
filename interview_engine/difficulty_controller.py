# ----------------------------------------------------
# DifficultyController Class
# ----------------------------------------------------

# This class manages the difficulty progression
# of interview questions
class DifficultyController:


    # ----------------------------------------------------
    # Constructor
    # ----------------------------------------------------

    def __init__(self):

        # Start interview at easy difficulty
        self.level = "easy"

        # Counter to track how many questions asked
        self.question_count = 0


    # ----------------------------------------------------
    # Update difficulty level
    # ----------------------------------------------------

    def update_difficulty(self):

        # Increase question count
        self.question_count += 1

        # After a few questions increase difficulty
        if self.question_count > 2:
            self.level = "medium"

        if self.question_count > 5:
            self.level = "hard"

        # Return current difficulty level
        return self.level