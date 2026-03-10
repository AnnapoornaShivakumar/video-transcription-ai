import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_slide_content(text):

    prompt = f"""
Create video slide information from this text.

Return JSON format:

{{
"title": "",
"bullets": ["", "", ""],
"image_query": ""
}}

Rules:
- title should summarize the idea
- bullets should be short phrases
- image_query should be a good stock photo search phrase

Text:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    content = response.choices[0].message.content

    # safety cleanup
    if not content:
        raise ValueError("Empty response from OpenAI")

    content = content.strip()

    # remove markdown if present
    content = content.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        print("Invalid JSON from LLM:")
        print(content)
        raise

    return data