# Class responsible for detecting filler words (speech disfluencies)
# Examples: "um", "uh", "like", "you know"

class DisfluencyDetector:

    def __init__(self):

        # List of common filler words used in casual speech
        # These words reduce fluency in interviews
        self.filler_words = [
            "um",
            "uh",
            "like",
            "you know",
            "actually",
            "basically",
            "sort of",
            "kind of",
            "i mean",
            "well",
            "so"
        ]


    def detect(self, text):

        # Convert text to lowercase for consistent matching
        text = text.lower()

        # Remove punctuation that may break matching
        text = text.replace(",", "").replace(".", "").replace("?", "")

        # Variable to store total filler count
        filler_count = 0

        # Store which fillers were found
        fillers_found = []

        # Loop through filler list
        for filler in self.filler_words:

            # Count how many times filler appears in text
            count = text.count(filler)

            if count > 0:

                # Add count to total filler count
                filler_count += count

                # Store filler word detected
                fillers_found.append(filler)


        # Return structured result
        return {

            # Total number of filler words detected
            "fillers": filler_count,

            # List of filler words detected
            "words": fillers_found
        }