# ----------------------------------------------------
# TopicTracker Class
# ----------------------------------------------------

class TopicTracker:

    def __init__(self):

        # Topics already discussed
        self.covered_topics = []


    # ----------------------------------------------------
    # Mark topic as covered
    # ----------------------------------------------------

    def add_topic(self, topic):

        if topic not in self.covered_topics:
            self.covered_topics.append(topic)


    # ----------------------------------------------------
    # Check if topic already discussed
    # ----------------------------------------------------

    def is_covered(self, topic):

        return topic in self.covered_topics