# ----------------------------------------------------
# Job Role Definitions
# ----------------------------------------------------
# Add or edit roles here anytime to expand the list

JOB_ROLES = {

    "software_engineer": {
        "title": "Software Engineer",
        "focus_skills": ["python", "data structures", "algorithms", "system design", "sql"],
        "description": "Backend/full-stack software development role",
        "key_topics": [
            "object-oriented programming",
            "REST APIs",
            "databases",
            "system design",
            "data structures and algorithms"
        ]
    },

    "data_scientist": {
        "title": "Data Scientist",
        "focus_skills": ["python", "machine learning", "statistics", "sql", "data analysis"],
        "description": "Data science and ML modeling role",
        "key_topics": [
            "machine learning models",
            "feature engineering",
            "model evaluation",
            "statistics",
            "data visualization"
        ]
    },

    "ml_engineer": {
        "title": "ML Engineer",
        "focus_skills": ["python", "machine learning", "deep learning", "mlops", "docker"],
        "description": "Machine learning engineering and deployment role",
        "key_topics": [
            "model training and deployment",
            "MLOps pipelines",
            "deep learning frameworks",
            "model optimization",
            "cloud infrastructure"
        ]
    },

    "cybersecurity_analyst": {
        "title": "Cybersecurity Analyst",
        "focus_skills": ["cybersecurity", "networking", "python", "linux", "ethical hacking"],
        "description": "Security analysis and threat detection role",
        "key_topics": [
            "network security",
            "penetration testing",
            "threat analysis",
            "encryption",
            "incident response"
        ]
    },

    "frontend_developer": {
        "title": "Frontend Developer",
        "focus_skills": ["javascript", "react", "html", "css", "typescript"],
        "description": "Frontend web development role",
        "key_topics": [
            "React/component architecture",
            "state management",
            "CSS layouts",
            "web performance",
            "browser APIs"
        ]
    },

    "devops_engineer": {
        "title": "DevOps Engineer",
        "focus_skills": ["docker", "kubernetes", "aws", "linux", "ci/cd"],
        "description": "DevOps and cloud infrastructure role",
        "key_topics": [
            "CI/CD pipelines",
            "containerization",
            "cloud services",
            "infrastructure as code",
            "monitoring and logging"
        ]
    },

    "android_developer": {
        "title": "Android Developer",
        "focus_skills": ["java", "kotlin", "android", "firebase", "rest apis"],
        "description": "Android mobile application development role",
        "key_topics": [
            "Android lifecycle",
            "Jetpack components",
            "REST API integration",
            "app architecture (MVVM)",
            "performance optimization"
        ]
    },

    "backend_developer": {
        "title": "Backend Developer",
        "focus_skills": ["python", "java", "sql", "rest apis", "system design"],
        "description": "Backend services and API development role",
        "key_topics": [
            "API design",
            "database optimization",
            "authentication and security",
            "microservices",
            "caching strategies"
        ]
    }
}


def get_role(role_key: str) -> dict:
    """Returns role config or a generic fallback."""
    role = JOB_ROLES.get(role_key)
    if role:
        # Return a copy to prevent mutating the global dictionary
        role_copy = role.copy()
        # Shallow copy is fine since lists are only read, but let's be safe
        role_copy["focus_skills"] = list(role["focus_skills"])
        role_copy["key_topics"] = list(role["key_topics"])
        return role_copy
    return {
        "title": "General Software Engineer",
        "focus_skills": [],
        "description": "General technical role",
        "key_topics": ["problem solving", "technical knowledge", "system design"]
    }


def list_roles() -> list:
    """Returns list of available role keys and titles for frontend dropdown."""
    return [{"key": k, "title": v["title"]} for k, v in JOB_ROLES.items()]