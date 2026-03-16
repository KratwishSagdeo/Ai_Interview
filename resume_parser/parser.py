# Import pdfplumber library
# This library allows us to extract text from PDF files
import pdfplumber


# ----------------------------------------------------
# ResumeParser Class
# ----------------------------------------------------

class ResumeParser:

    # Constructor
    # Runs automatically when the class is created
    def __init__(self):
        pass


    # ----------------------------------------------------
    # Function to extract text from PDF
    # ----------------------------------------------------

    def extract_text(self, pdf_path):

        # Initialize empty string to store resume text
        text = ""

        # Open the PDF file
        with pdfplumber.open(pdf_path) as pdf:

            # Loop through every page in the PDF
            for page in pdf.pages:

                # Extract text from the current page
                page_text = page.extract_text()

                # If text exists add it to the main string
                if page_text:
                    text += page_text + "\n"

        # Return the full extracted resume text
        return text