import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from interview_engine.interview_manager import InterviewManager

try:
    mgr = InterviewManager()

    # Start interview
    first_q = mgr.start_interview("dummy_resume.pdf")
    print("First Question:", first_q)

    print("MGR Init success")

    # Process answer
    res = mgr.process_answer("yes I am a programmer", None)
    print("SUCCESS", res)

except Exception as e:
    import traceback
    traceback.print_exc()