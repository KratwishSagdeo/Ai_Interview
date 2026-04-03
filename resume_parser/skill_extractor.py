import re
import spacy

nlp = spacy.load("en_core_web_sm")


class SkillExtractor:

    def __init__(self):

        self.skill_keywords = [
            "python", "java", "c++", "c#", "javascript", "typescript",
            "kotlin", "swift", "go", "rust", "php", "ruby", "scala",
            "r", "matlab", "bash", "shell", "dart", "c",
            "machine learning", "deep learning", "neural network",
            "natural language processing", "nlp", "computer vision",
            "reinforcement learning", "transfer learning",
            "xgboost", "random forest", "gradient boosting",
            "decision tree", "linear regression", "logistic regression",
            "svm", "k-means", "clustering", "tensorflow", "pytorch",
            "keras", "scikit-learn", "sklearn", "hugging face",
            "transformers", "bert", "gpt", "llm", "openai", "langchain",
            "pandas", "numpy", "matplotlib", "opencv", "yolo", "cnn",
            "fastapi", "flask", "django", "node.js", "express",
            "react", "angular", "vue", "next.js", "html", "css",
            "rest api", "graphql", "websocket", "microservices",
            "android", "ios", "flutter", "react native", "firebase",
            "jetpack", "mvvm", "retrofit",
            "sql", "mysql", "postgresql", "mongodb", "redis",
            "elasticsearch", "sqlite", "nosql", "data structures",
            "algorithms", "data analysis", "spark", "hadoop",
            "aws", "azure", "gcp", "google cloud", "docker",
            "kubernetes", "terraform", "ci/cd", "linux", "git", "devops",
            "cybersecurity", "cyber security", "network security",
            "penetration testing", "ethical hacking", "kali linux",
            "wireshark", "encryption", "cryptography",
            "app development", "mobile development", "web development",
            "software development", "full stack", "backend", "frontend",
            "object oriented", "oop", "system design", "api",
        ]

    def extract_skills(self, resume_text):
        text = resume_text.lower()
        seen = set()
        skills = []
        for skill in self.skill_keywords:
            if skill in text and skill not in seen:
                seen.add(skill)
                skills.append(skill)
        return skills

    def extract_resume_context(self, resume_text):
        """
        Extracts every useful detail from the resume for personalised questioning.
        Returns a rich structured string passed directly to the LLM.
        """

        lines = [l.strip() for l in resume_text.split("\n") if l.strip()]
        result = {}

        # Name — usually first line
        result["name"] = lines[0] if lines else "Candidate"

        # Education
        edu_lines = []
        edu_kw = ["b.tech", "btech", "b.e", "m.tech", "mtech", "bca", "mca",
                  "bachelor", "master", "phd", "university", "college",
                  "institute", "btec", "b.sc", "m.sc", "cgpa", "gpa",
                  "percentage", "10th", "12th", "diploma"]
        for line in lines:
            if any(kw in line.lower() for kw in edu_kw):
                edu_lines.append(line)
        result["education"] = edu_lines[:4]

        # Projects — capture full project descriptions
        projects = []
        current = []
        in_proj = False
        for line in lines:
            ll = line.lower()
            if any(kw in ll for kw in ["project", "built", "developed", "implemented", "created"]):
                in_proj = True
                if current:
                    projects.append(" | ".join(current))
                    current = []
            if in_proj and len(line) > 15:
                current.append(line)
                if len(current) >= 4:
                    projects.append(" | ".join(current))
                    current = []
                    in_proj = False
        if current:
            projects.append(" | ".join(current))
        result["projects"] = projects[:5]

        # Experience / internships
        exp_lines = []
        in_exp = False
        for line in lines:
            ll = line.lower()
            if any(kw in ll for kw in ["experience", "internship", "intern",
                                        "worked", "employment", "position"]):
                in_exp = True
            if in_exp and len(line) > 10:
                exp_lines.append(line)
            if len(exp_lines) >= 6:
                break
        result["experience"] = exp_lines[:6]

        # Certifications and achievements
        cert_lines = []
        for line in lines:
            ll = line.lower()
            if any(kw in ll for kw in ["certif", "certified", "achievement",
                                        "award", "winner", "hackathon",
                                        "rank", "publication", "research"]):
                cert_lines.append(line)
        result["certifications"] = cert_lines[:4]

        # Build LLM-ready summary
        parts = [f"Candidate name: {result['name']}"]

        if result["education"]:
            parts.append("Education:\n" + "\n".join(f"  - {e}" for e in result["education"]))

        if result["experience"]:
            parts.append("Work experience / internships:\n" + "\n".join(f"  - {e}" for e in result["experience"]))

        if result["projects"]:
            parts.append("Projects:\n" + "\n".join(f"  - {p}" for p in result["projects"]))

        if result["certifications"]:
            parts.append("Certifications / achievements:\n" + "\n".join(f"  - {c}" for c in result["certifications"]))

        # Fallback
        if len(parts) < 2:
            parts = [f"Resume content:\n{resume_text[:500].replace(chr(10), ' ')}"]

        return "\n\n".join(parts)