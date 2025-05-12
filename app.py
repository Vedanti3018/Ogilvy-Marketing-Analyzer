import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
from dotenv import load_dotenv
from urllib.parse import urlparse
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer,Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
from validators import url as validate_url
import re
import tempfile

load_dotenv()  # load variables from .env

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_ID = "llama-3.3-70b-versatile"
API_URL = f"https://api.groq.com/openai/v1/chat/completions"

# Ogilvy Principles Prompt
OGILVY_PROMPT_TEMPLATE = """
You are an advertising strategist trained in David Ogilvy’s principles.

Task:
1. Visit the user-provided URL.
2. Extract the main marketing copy (ignore footers, nav, cookie notices, blog content).
3. Score the copy out of 100 using the 15 Ogilvy-inspired principles (each ~6.7 points).
4. Provide a detailed score breakdown.
5. Identify the top 3 improvement areas.
6. Suggest edits to improve the score.
7. Rewrite the copy to achieve 100/100.

### 15 Scoring Criteria:

1. Product Positioning
2. Unique Benefit
3. Headline
4. Reader-Focused
5. Clear Tone
6. Simple Language
7. Evidence
8. Emotion/Story
9. Structure
10. Call-to-Action
11. Visuals/Captions
12. Testability
13. Length
14. Attention-Grabbing
15. Repetition

---

### URL Analyzed: {url}

### Website Content:
\"\"\"
{content}
\"\"\"

---

Now perform the analysis and return results in this format:

**Overall Score:** X/100

**Score Breakdown:**
| Principle | Score (0–6.7) | Comments |
|-----------|----------------|----------|
| 1. Product Positioning | X.X | ... |
...

**Top 3 Areas to Improve:**
1. ...
2. ...
3. ...

**Rewrite (to score 100/100):**
[Rewritten copy]
"""

# Function to extract main marketing content from a webpage
def get_domain_from_url(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace("www.", "").split(".")[0].capitalize()
    return domain

def extract_main_text(url):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.content, "html.parser")
        for tag in soup(["header", "footer", "nav", "script", "style", "noscript", "svg"]):
            tag.decompose()
        text_blocks = soup.find_all(["p", "h1", "h2", "h3", "h4", "span"])
        visible_text = " ".join(tag.get_text(separator=" ", strip=True) for tag in text_blocks)
        return visible_text[:8000]  # limit to avoid token overflow
    except Exception as e:
        st.error(f"Failed to extract text: {e}")
        return None

def analyze_with_groq(prompt):
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_API_KEY:
        st.error("Missing GROQ_API_KEY in environment variables.")
        st.stop()

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": "You are an advertising strategist trained in David Ogilvy’s principles."},
            {"role": "user", "content": prompt}
        ]
    }
    res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    return res.json()['choices'][0]['message']['content']


def generate_pdf_report(domain, analysis, improvements, rewrite):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title=f"{domain} Ogilvy Report",
                            rightMargin=40, leftMargin=40, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    heading = styles["Heading2"]

    # Custom style for wrapped table cells
    wrapped_style = ParagraphStyle('wrapped_style', parent=normal, fontSize=10, leading=12)

    story = []

    # Title
    story.append(Paragraph(f"{domain} – Ogilvy Marketing Analyzer Report", styles["Title"]))
    story.append(Spacer(1, 0.3 * inch))

    # Score Header
    story.append(Paragraph("Ogilvy Score Breakdown", heading))
    story.append(Spacer(1, 0.2 * inch))

    # Extract table from analysis text
    table_match = re.search(r"\| Principle.*?\|\s*\*\*Top 3", analysis, re.DOTALL)
    if table_match:
        table_block = table_match.group(0).strip().split("\n")
        table_data = []

        for row in table_block:
            if '|' in row:
                cells = [Paragraph(cell.strip(), wrapped_style) for cell in row.strip('|').split('|')]
                table_data.append(cells)

        col_widths = [1.8 * inch, 1.2 * inch, 3.5 * inch]  # Adjust based on content
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No table data found in analysis.", normal))

    story.append(Spacer(1, 0.4 * inch))

    # Top 3 Improvement Areas
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Top 3 Improvement Areas", heading))
    story.append(Spacer(1, 0.15 * inch))
    for line in improvements.strip().split('\n'):
        if line.strip():
            formatted_line = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", line.strip())
            story.append(Paragraph("• " + formatted_line, wrapped_style))
            story.append(Spacer(1, 0.05 * inch))

    story.append(Spacer(1, 0.4 * inch))

    # Optimized Rewritten Copy
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Optimized Rewritten Copy", heading))
    story.append(Spacer(1, 0.15 * inch))
    for para in rewrite.strip().split('\n\n'):
        formatted_para = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", para.strip())
        formatted_para = formatted_para.replace('\n', '<br/>')
        story.append(Paragraph(formatted_para, wrapped_style))
        story.append(Spacer(1, 0.1 * inch))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ---------------- Streamlit UI ----------------
st.set_page_config(page_title="Ogilvy Marketing Analyzer", layout="wide")
st.title("📊 Ogilvy Marketing Analyzer")
url = st.text_input("Enter a website URL to analyze")

if url:
    if not validate_url(url):
        st.warning("Please enter a valid URL.")
        st.stop()

    if st.button("Analyze"):
        content = extract_main_text(url)
        if content:
            if len(content) > 4000:
                content = content[:4000] + "\n\n[Content truncated for analysis...]"

            with st.spinner("Analyzing copy using Ogilvy principles..."):
                prompt = OGILVY_PROMPT_TEMPLATE.format(url=url, content=content)
                result = analyze_with_groq(prompt)

                # Parse result
                try:
                    sections = result.split("**Rewrite (to score 100/100):**")
                    analysis = sections[0].strip()
                    rewrite = sections[1].strip() if len(sections) > 1 else "Rewrite not found."

                    st.markdown("### 🧠 Ogilvy Score & Breakdown")
                    st.markdown(analysis)

                    st.markdown("### ✍️ Optimized Rewritten Copy")
                    st.text_area("Rewritten Marketing Copy", value=rewrite, height=300)

                    # Generate PDF and show download button
                    domain = get_domain_from_url(url)
                    # Extract "Top 3 Areas to Improve" section
                    improvements_match = re.search(r"\*\*Top 3 Areas to Improve:\*\*(.*?)\*\*Rewrite", result,
                                                   re.DOTALL)
                    improvements = improvements_match.group(1).strip() if improvements_match else "Not found."

                    pdf_buffer = generate_pdf_report(domain, analysis, improvements, rewrite)
                    st.download_button(
                        label="📥 Download Report as PDF",
                        data=pdf_buffer,
                        file_name=f"{domain}_Ogilvy_Marketing_Analyzer.pdf",
                        mime="application/pdf"
                    )

                except Exception as e:
                    st.error(f"Failed to parse the output: {e}")
                    st.text(result)  # fallback raw output
