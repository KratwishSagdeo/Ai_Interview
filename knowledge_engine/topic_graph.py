# ----------------------------------------------------
# TopicGraph Class
# ----------------------------------------------------

# This class stores relationships between concepts
class TopicGraph:

    def __init__(self):

        # Define topic relationships
        # Each topic has related subtopics
        self.graph = {

            "python": [
                "lists",
                "tuples",
                "dictionaries",
                "generators",
                "decorators"
            ],

            "machine learning": [
                "gradient descent",
                "overfitting",
                "bias variance",
                "regularization"
            ],

            "docker": [
                "containers",
                "images",
                "dockerfile",
                "kubernetes"
            ],

            "cybersecurity": [
                "malware",
                "encryption",
                "network security",
                "penetration testing"
            ]
        }


    # ----------------------------------------------------
    # Get related topics
    # ----------------------------------------------------

    def get_related_topics(self, topic):

        # Convert topic to lowercase
        topic = topic.lower()

        # Return related topics if available
        if topic in self.graph:
            return self.graph[topic]

        return []