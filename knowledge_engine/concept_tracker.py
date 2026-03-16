# ----------------------------------------------------
# Import spaCy NLP library
# ----------------------------------------------------

# spaCy is used for natural language processing
# It allows us to extract nouns, entities, and key concepts
import spacy


# Load English NLP model
# This model contains linguistic rules and vocabulary
nlp = spacy.load("en_core_web_sm")


# ----------------------------------------------------
# ConceptExtractor Class
# ----------------------------------------------------

class ConceptExtractor:


    # ----------------------------------------------------
    # Extract concepts from answer
    # ----------------------------------------------------

    def extract_concepts(self, text):

        # Process text with spaCy NLP pipeline
        doc = nlp(text)

        # List to store extracted concepts
        concepts = []

        # Loop through tokens in sentence
        for token in doc:

            # Check if token is a noun or proper noun
            # Most technical concepts appear as nouns
            if token.pos_ in ["NOUN", "PROPN"]:

                # Convert word to lowercase
                concept = token.text.lower()

                # Add concept to list
                concepts.append(concept)

        # Remove duplicates
        concepts = list(set(concepts))

        # Return detected concepts
        return concepts