import os
import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import Color

class PDFReportGenerator:
    def __init__(self):
        self.PRIMARY = Color(37/255, 99/255, 235/255)
        self.SUCCESS = Color(22/255, 163/255, 74/255)
        self.WARNING = Color(217/255, 119/255, 6/255)
        self.DANGER = Color(220/255, 38/255, 38/255)
        self.LIGHT = Color(241/255, 245/255, 249/255)
        self.DARK = Color(30/255, 41/255, 59/255)
        self.width, self.height = A4
        self.margin = 40
        self.current_page = 1

    def _add_footer(self):
        self.c.setFont("Helvetica", 10)
        self.c.setFillColor(self.DARK)
        self.c.drawRightString(self.width - self.margin, 20, f"Page {self.current_page} - AI Interview Platform - Confidential")
        self.current_page += 1

    def _draw_section_title(self, x, y, title):
        self.c.setFillColor(self.PRIMARY)
        self.c.rect(x, y - 18, 3, 22, fill=True, stroke=False)
        self.c.setFillColor(self.DARK)
        self.c.setFont("Helvetica-Bold", 18)
        self.c.drawString(x + 10, y - 14, title)
        return y - 40

    def generate(self, report: dict, output_path: str) -> str:
        self.c = canvas.Canvas(output_path, pagesize=A4)
        self.report = report
        self.current_page = 1
        
        self._draw_page_1()
        self._add_footer()
        self.c.showPage()
        
        self._draw_page_2()
        self._add_footer()
        self.c.showPage()
        
        self._draw_page_3()
        self._add_footer()
        self.c.showPage()
        
        self._draw_page_qa()
        
        self.c.save()
        return output_path

    def _draw_page_1(self):
        session = self.report.get("session_summary", {})
        
        self.c.setFont("Helvetica-Bold", 28)
        self.c.setFillColor(self.DARK)
        self.c.drawString(self.margin, self.height - 100, "AI Mock Interview Report")
        
        self.c.setFont("Helvetica-Oblique", 20)
        self.c.setFillColor(self.PRIMARY)
        self.c.drawString(self.margin, self.height - 140, session.get("job_role", "Candidate"))
        
        # Badge
        band = session.get("performance_band", "Moderate")
        if band.lower() == "strong":
            badge_color = self.SUCCESS
        elif band.lower() == "needs improvement":
            badge_color = self.DANGER
        else:
            badge_color = self.WARNING
            
        self.c.setFillColor(badge_color)
        self.c.roundRect(self.margin, self.height - 185, 150, 25, 10, fill=True, stroke=False)
        self.c.setFillColor(Color(1,1,1))
        self.c.setFont("Helvetica-Bold", 12)
        self.c.drawCentredString(self.margin + 75, self.height - 177, band.upper())
        
        # Date
        self.c.setFillColor(self.DARK)
        self.c.setFont("Helvetica", 14)
        date_str = datetime.datetime.now().strftime("%B %d, %Y")
        self.c.drawString(self.margin, self.height - 230, f"Generated on: {date_str}")
        
        # Overall Score
        score = session.get("overall_score", 0) * 100
        self.c.setFont("Helvetica-Bold", 60)
        self.c.setFillColor(self.PRIMARY)
        self.c.drawString(self.margin, self.height - 320, f"{score:.0f}%")
        self.c.setFont("Helvetica", 16)
        self.c.setFillColor(self.DARK)
        self.c.drawString(self.margin, self.height - 340, "Overall Performance Score")
        
        self.c.setStrokeColor(self.LIGHT)
        self.c.line(self.margin, self.height - 380, self.width - self.margin, self.height - 380)

    def _get_color_for_score(self, percent):
        if percent < 40: return self.DANGER
        if percent < 70: return self.WARNING
        return self.SUCCESS

    def _draw_page_2(self):
        y = self.height - 80
        y = self._draw_section_title(self.margin, y, "Performance Overview")
        
        # Boxes
        c_score = self.report.get("content_scores", {}).get("average_content_score", 0) * 100
        f_score = self.report.get("fluency_scores", {}).get("overall_fluency_score", 0)
        
        box_w = (self.width - 2 * self.margin - 20) / 2
        
        # Box 1
        self.c.setFillColor(self.LIGHT)
        self.c.roundRect(self.margin, y - 80, box_w, 80, 5, fill=True, stroke=False)
        self.c.setFillColor(self.DARK)
        self.c.setFont("Helvetica-Bold", 14)
        self.c.drawString(self.margin + 10, y - 30, "Content Score")
        self.c.setFont("Helvetica-Bold", 24)
        self.c.drawString(self.margin + 10, y - 60, f"{c_score:.0f}%")
        
        c_color = self._get_color_for_score(c_score)
        self.c.setFillColor(c_color)
        self.c.rect(self.margin + 10, y - 70, (box_w - 20) * (c_score/100), 5, fill=True, stroke=False)
        
        # Box 2
        x2 = self.margin + box_w + 20
        self.c.setFillColor(self.LIGHT)
        self.c.roundRect(x2, y - 80, box_w, 80, 5, fill=True, stroke=False)
        self.c.setFillColor(self.DARK)
        self.c.setFont("Helvetica-Bold", 14)
        self.c.drawString(x2 + 10, y - 30, "Fluency Score")
        self.c.setFont("Helvetica-Bold", 24)
        self.c.drawString(x2 + 10, y - 60, f"{f_score:.0f}")
        
        f_color = self._get_color_for_score(f_score)
        self.c.setFillColor(f_color)
        self.c.rect(x2 + 10, y - 70, (box_w - 20) * (f_score/100), 5, fill=True, stroke=False)
        
        y -= 120
        
        # Confidence Chart
        self.c.setFillColor(self.DARK)
        self.c.setFont("Helvetica-Bold", 14)
        self.c.drawString(self.margin, y, "Confidence Progression Throughout Interview")
        y -= 20
        
        hist = self.report.get("content_scores", {}).get("confidence_history", [])
        chart_h = 100
        chart_w = self.width - 2 * self.margin
        
        self.c.setStrokeColor(self.LIGHT)
        self.c.rect(self.margin, y - chart_h, chart_w, chart_h, fill=False, stroke=True)
        
        if not hist:
            self.c.setFont("Helvetica", 12)
            self.c.drawCentredString(self.width/2, y - chart_h/2, "No data available")
        else:
            self.c.setStrokeColor(self.PRIMARY)
            self.c.setLineWidth(2)
            
            pts = len(hist)
            if pts > 1:
                dx = chart_w / (pts - 1)
                for i in range(pts - 1):
                    x1 = self.margin + i * dx
                    y1 = y - chart_h + hist[i] * chart_h
                    x2 = self.margin + (i+1) * dx
                    y2 = y - chart_h + hist[i+1] * chart_h
                    self.c.line(x1, y1, x2, y2)
            else:
                x1 = self.margin + chart_w/2
                y1 = y - chart_h + hist[0] * chart_h
                self.c.circle(x1, y1, 3, fill=True)
                
        self.c.setLineWidth(1)
        y -= (chart_h + 40)
        
        # Fluency Metrics Grid
        f_data = self.report.get("fluency_scores", {})
        metrics = [
            ("Speech Rate", f"{f_data.get('avg_speech_rate_wpm', 0):.1f} WPM"),
            ("Avg Pauses", f"{f_data.get('avg_pause_count', 0):.1f} /ans"),
            ("Filler Words", f"{f_data.get('avg_filler_words', 0):.1f} /ans"),
            ("Vocabulary Diversity", f"{f_data.get('avg_lexical_diversity', 0)*100:.0f}%")
        ]
        
        gw = (self.width - 2 * self.margin - 20) / 2
        gh = 50
        
        for i, (m_title, m_val) in enumerate(metrics):
            row = i // 2
            col = i % 2
            bx = self.margin + col * (gw + 20)
            by = y - row * (gh + 10) - gh
            
            self.c.setFillColor(self.LIGHT)
            self.c.roundRect(bx, by, gw, gh, 5, fill=True, stroke=False)
            
            self.c.setFillColor(self.DARK)
            self.c.setFont("Helvetica", 12)
            self.c.drawString(bx + 10, by + gh - 20, m_title)
            
            self.c.setFont("Helvetica-Bold", 14)
            self.c.drawString(bx + 10, by + 10, str(m_val))

    def _draw_page_3(self):
        y = self.height - 80
        
        session = self.report.get("session_summary", {})
        skills = session.get("skills_detected", [])
        
        y = self._draw_section_title(self.margin, y, "Skills Detected")
        
        # Pills
        colors = [self.PRIMARY, Color(20/255, 184/255, 166/255), Color(168/255, 85/255, 247/255)] # Blue, Teal, Purple
        px = self.margin
        for i, skill in enumerate(skills):
            self.c.setFont("Helvetica", 12)
            sw = self.c.stringWidth(skill, "Helvetica", 12)
            if px + sw + 20 > self.width - self.margin:
                px = self.margin
                y -= 30
            
            self.c.setFillColor(colors[i % len(colors)])
            self.c.roundRect(px, y - 20, sw + 20, 25, 12, fill=True, stroke=False)
            self.c.setFillColor(Color(1,1,1))
            self.c.drawString(px + 10, y - 13, skill)
            px += sw + 30
            
        y -= 50
        
        weaks = session.get("weak_areas", [])
        y = self._draw_section_title(self.margin, y, "Areas for Improvement")
        px = self.margin
        for weak in weaks:
            self.c.setFont("Helvetica", 12)
            sw = self.c.stringWidth(weak, "Helvetica", 12)
            if px + sw + 20 > self.width - self.margin:
                px = self.margin
                y -= 30
                
            self.c.setFillColor(self.DANGER)
            self.c.roundRect(px, y - 20, sw + 20, 25, 12, fill=True, stroke=False)
            self.c.setFillColor(Color(1,1,1))
            self.c.drawString(px + 10, y - 13, weak)
            px += sw + 30
            
        y -= 50
        
        feedback = self.report.get("feedback", [])
        y = self._draw_section_title(self.margin, y, "Interviewer Feedback")
        
        for idx, fb in enumerate(feedback):
            is_positive = idx % 2 == 0 # Simplistic determination based on instructions
            # Or just alternating for now if we can't tell, but I will make it green/orange interchangeably
            dot_color = self.SUCCESS if ("strong" in fb.lower() or "good" in fb.lower() or "natural" in fb.lower()) else self.WARNING
            
            self.c.setFillColor(dot_color)
            self.c.circle(self.margin + 5, y - 5, 4, fill=True, stroke=False)
            
            self.c.setFillColor(self.DARK)
            self.c.setFont("Helvetica", 12)
            
            # Text wrapping
            # simple wrap
            words = fb.split()
            line = ""
            cy = y - 10
            for w in words:
                if self.c.stringWidth(line + w + " ", "Helvetica", 12) < self.width - 2*self.margin - 20:
                    line += w + " "
                else:
                    self.c.drawString(self.margin + 20, cy, line)
                    line = w + " "
                    cy -= 15
            self.c.drawString(self.margin + 20, cy, line)
            y = cy - 20

    def _draw_page_qa(self):
        y = self.height - 80
        qa_log = self.report.get("qa_log", [])
        
        y = self._draw_section_title(self.margin, y, "Interview Questions & Answers")
        
        if not qa_log:
            self.c.setFont("Helvetica", 12)
            self.c.setFillColor(self.DARK)
            self.c.drawString(self.margin, y - 20, "No questions recorded")
            self._add_footer()
            self.c.showPage()
            return
            
        for qa in qa_log:
            if y < 100:
                self._add_footer()
                self.c.showPage()
                y = self.height - 80
                
            q_num = qa.get("question_number", 0)
            q_text = qa.get("question", "")
            a_text = qa.get("answer_preview", "")
            
            # Circle
            self.c.setFillColor(self.PRIMARY)
            self.c.circle(self.margin + 10, y - 10, 10, fill=True, stroke=False)
            self.c.setFillColor(Color(1,1,1))
            self.c.setFont("Helvetica-Bold", 10)
            self.c.drawCentredString(self.margin + 10, y - 13, str(q_num))
            
            # Question
            self.c.setFillColor(self.DARK)
            self.c.setFont("Helvetica-Bold", 12)
            
            def wrap_text(c, text, x_st, y_st, font, size, max_w):
                c.setFont(font, size)
                words = text.split()
                line = ""
                cy = y_st
                for w in words:
                    if c.stringWidth(line + w + " ", font, size) < max_w:
                        line += w + " "
                    else:
                        c.drawString(x_st, cy, line)
                        line = w + " "
                        cy -= 15
                c.drawString(x_st, cy, line)
                return cy - 20

            y = wrap_text(self.c, q_text, self.margin + 30, y - 13, "Helvetica-Bold", 12, self.width - 2*self.margin - 30)
            
            # Answer
            self.c.setFillColor(self.DARK)
            y = wrap_text(self.c, a_text, self.margin + 40, y + 5, "Helvetica", 11, self.width - 2*self.margin - 40)
            
            y -= 10
            self.c.setStrokeColor(self.LIGHT)
            self.c.line(self.margin, y, self.width - self.margin, y)
            y -= 20
            
        self._add_footer()
        # Ensure last page gets flushed: wait, in generate() we do self.c.save() after QA, so it's fine.
