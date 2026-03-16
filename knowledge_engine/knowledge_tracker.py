# ----------------------------------------------------
# KnowledgeTracker Class
# ----------------------------------------------------

class KnowledgeTracker:


    # ----------------------------------------------------
    # Constructor
    # ----------------------------------------------------

    def __init__(self):

        # Store all detected concepts
        self.known_concepts = []

        # Store weak areas
        self.weak_concepts = []


    # ----------------------------------------------------
    # Update knowledge graph
    # ----------------------------------------------------

    def update_knowledge(self, concepts):

        # Loop through detected concepts
        for concept in concepts:

            # If concept not already stored
            if concept not in self.known_concepts:

                # Add concept to knowledge graph
                self.known_concepts.append(concept)


    # ----------------------------------------------------
    # Detect missing concepts
    # ----------------------------------------------------

    def detect_missing_concepts(self, expected_concepts):

        # Loop through expected concepts
        for concept in expected_concepts:

            # If candidate did not mention concept
            if concept not in self.known_concepts:

                # Add to weak concept list
                self.weak_concepts.append(concept)

        # Return weak concepts
        return self.weak_concepts