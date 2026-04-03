import os
import requests
import uuid
from dotenv import load_dotenv

load_dotenv()
API_BASE = "http://localhost:8000"
API_KEY = os.getenv("INTERVIEW_API_KEY", "")
HEADERS = {"X-API-Key": API_KEY}

print("1. Getting job roles...")
roles = requests.get(f"{API_BASE}/job-roles", timeout=10).json()
print("Roles defined:", len(roles.get("roles", [])))

print("\n2. Uploading resume...")

try:
    with open("temp_resume_Kratwish_Sagdeo.pdf", "rb") as f:
        files = {"file": ("temp_resume_Kratwish_Sagdeo.pdf", f, "application/pdf")}
        res = requests.post(f"{API_BASE}/upload-resume", files=files, data={"job_role": "software_engineer"}, headers=HEADERS, timeout=60)
    
    print("Response Code:", res.status_code)
    try:
        json_res = res.json()
        print("Response JSON:", json_res)
    except:
        print("Raw response:", res.text)
        json_res = {}
    
    session_id = json_res.get("session_id")
    question = json_res.get("question")
    
    print(f"\n3. Session ID: {session_id}")
    print(f"First Question: {question}")
    
    print("\n4. Validating UUID...")
    uuid.UUID(str(session_id))
    print("UUID is valid!")
except Exception as e:
    import traceback
    traceback.print_exc()
