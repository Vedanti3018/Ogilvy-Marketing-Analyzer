import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
from dotenv import load_dotenv
import os

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
def extract_main_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        page = requests.get(url, headers=headers)
        soup = BeautifulSoup(page.text, 'html.parser')

        # Remove footer, nav, scripts
        for tag in soup(['script', 'style', 'footer', 'nav', 'noscript']):
            tag.decompose()

        # Get main text content
        text = soup.get_text(separator='\n')
        lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 40]
        return '\n'.join(lines[:50])  # Limit to ~50 relevant lines
    except Exception as e:
        return f"Error extracting text: {e}"

# Function to call Groq API
def analyze_with_groq(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": "You are a copywriting evaluator and strategist."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()["choices"][0]["message"]["content"]

# Streamlit UI
st.title("📊 Ogilvy Marketing Analyzer")
url = st.text_input("Enter URL to analyze")

if url:
    if st.button("Analyze"):
        content = extract_main_text(url)
        if content:
            with st.spinner("Analyzing..."):
                prompt = OGILVY_PROMPT_TEMPLATE.format(url=url, content=content)
                result = analyze_with_groq(prompt)

            # Split response into sections
            try:
                # Try to extract the rewrite part
                sections = result.split("**Rewrite (to score 100/100):**")
                analysis = sections[0].strip()
                rewrite = sections[1].strip() if len(sections) > 1 else "Rewrite section not found."

                # Show the rest of the analysis
                st.markdown("### 🧠 Ogilvy Analysis")
                st.markdown(analysis)

                # Show the rewrite in a text box
                st.markdown("### ✍️ Rewritten Copy (100/100 Score)")
                st.text_area("Optimized Marketing Copy", value=rewrite, height=300)

            except Exception as e:
                st.error(f"Failed to parse Groq output: {e}")
                st.text(result)  # fallback raw output
