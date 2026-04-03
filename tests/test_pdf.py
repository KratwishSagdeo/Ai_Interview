import os
from services.pdf_generator import PDFReportGenerator

def test_pdf_generation():
    report = {
      "session_summary": {
        "job_role": "Software Engineer",
        "total_questions": 12,
        "total_answers": 12,
        "skills_detected": ["python", "machine learning", "docker"],
        "weak_areas": ["problem solving"],
        "end_reason": "all_stages_done",
        "performance_band": "Moderate",
        "overall_score": 0.65,
        "final_confidence": 0.72
      },
      "content_scores": {
        "average_content_score": 0.61,
        "total_evaluated": 12,
        "confidence_history": [0.3, 0.45, 0.52, 0.6, 0.65, 0.7, 0.72]
      },
      "fluency_scores": {
        "overall_fluency_score": 68.5,
        "avg_speech_rate_wpm": 142.3,
        "avg_pause_count": 1.2,
        "avg_filler_words": 2.1,
        "avg_grammar_errors": 0.4,
        "avg_lexical_diversity": 0.61
      },
      "feedback": [
        "Strong technical knowledge demonstrated.",
        "Speech rate was natural and easy to follow.",
        "Some filler words detected — minor but worth reducing."
      ],
    }
    
    qa_log = []
    for i in range(1, 21):
        qa_log.append({
            "question_number": i,
            "question": f"Question {i}: Could you give us an example of a time when you had to solve a complex problem?",
            "answer_preview": f"Answer {i}: I encountered a situation where the database performance was degrading. I analyzed the query logs, identified missing indexes, and optimized the table structure which resulted in a 5x speedup."
        })
    
    report["qa_log"] = qa_log

    output_path = "test_report.pdf"
    
    # Generate PDF
    generator = PDFReportGenerator()
    generator.generate(report, output_path)
    
    # Check
    assert os.path.exists(output_path), "File not created"
    
    size = os.path.getsize(output_path)
    assert size > 10240, f"File size too small: {size} bytes"
    
    print(f"PDF generated successfully: {output_path}")

if __name__ == "__main__":
    test_pdf_generation()
