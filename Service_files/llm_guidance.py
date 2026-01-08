import os
import requests
from dotenv import load_dotenv
import re

load_dotenv()

LLM_API_URL = os.getenv("LLM_API_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {LLM_API_KEY}",
    "Content-Type": "application/json"
}


def fallback_mentor_guidance(analysis):
    strengths = []
    weaknesses = []
    suggestions = []

    if analysis["education"]["match"] == "matched":
        strengths.append(
            "You meet the education requirement mentioned in the job description."
        )
    else:
        weaknesses.append(
            "Your education does not clearly match the job requirement."
        )

    if analysis["projects"]["has_projects"]:
        strengths.append(
            "Your resume includes projects, which is a strong positive signal."
        )
    else:
        weaknesses.append(
            "Your resume does not clearly mention any projects."
        )

    if analysis["experience"]["resume_domains"]:
        strengths.append(
            f"You mention relevant domains such as "
            f"{', '.join(analysis['experience']['resume_domains'])}."
        )

    missing_skills = [
        skill for skill, data in analysis["skills"]["semantic_skill_analysis"].items()
        if data["status"] == "missing"
    ]

    if missing_skills:
        weaknesses.append(
            "Several important technical skills required by the job "
            "are not clearly demonstrated in your resume."
        )
        suggestions.append(
            "Rewrite your project descriptions to explicitly mention tools "
            "like Python, machine learning libraries, frameworks, Git, and deployment tools."
        )

    response = "Here is a mentor-style review of your resume:\n\n"

    if strengths:
        response += "✅ Strengths:\n"
        for s in strengths:
            response += f"- {s}\n"

    if weaknesses:
        response += "\n⚠ Areas to improve:\n"
        for w in weaknesses:
            response += f"- {w}\n"

    if suggestions:
        response += "\n🎯 Suggestions:\n"
        for sug in suggestions:
            response += f"- {sug}\n"

    response += (
        "\nOverall, your profile shows good potential. "
        "Improving how clearly you present your technical skills and projects "
        "will significantly increase your chances of matching this role."
    )

    return response


import re

def format_guidance_for_html(guidance_text):
    """
    Organize LLM text by section headings and remove excessive empty lines.
    Returns a dict: {section_name: [list of paragraphs]}
    """
    sections = {}

    # Remove excessive newlines first
    guidance_text = re.sub(r'\n{2,}', '\n', guidance_text.strip())

    # Find headings like "Strengths:", "Skills Gaps:", etc.
    pattern = r'([A-Za-z\s]+:)'  # headings ending with colon
    splits = re.split(pattern, guidance_text)

    # If text starts with heading, splits[0] may be empty
    i = 0
    if not splits[0].strip():
        i = 1  # start from first heading
    else:
        sections["Intro"] = [splits[0].strip()]

    while i < len(splits) - 1:
        heading = splits[i].strip().rstrip(":")
        content = splits[i + 1].strip()
        # Split into paragraphs, remove empty ones
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        sections[heading] = paragraphs
        i += 2

    return sections



def generate_resume_guidance(analysis_json):
    if not LLM_API_URL or not LLM_API_KEY:
        print("❌ LLM DEBUG: Missing URL or API key")
        fallback_text = fallback_mentor_guidance(analysis_json)
        intro, bullets = format_guidance_for_html(fallback_text)
        return {
            "text": fallback_text,
            "source": "rule_based",
            "intro": intro,
            "bullets": bullets
        }

    prompt = f"""
You are a senior hiring mentor reviewing a resume against a job description.

Your response MUST:
1. First explain what the resume already does well for this role.
2. Then explain weak or missing areas and why they matter.
3. Give specific, practical suggestions on how the candidate can improve:
    - what skills to highlight better
    - what projects to add or modify
    - how to rewrite resume bullet points
4. Sound like a mentor guiding a junior candidate.
5. Avoid generic advice and avoid listing raw scores.

Please structure your response under these headings:
- Strengths
- Skills Gaps
- Experience Improvements
- Projects Suggestions
- Certifications
- Formatting Tips

Resume vs JD analysis:
{analysis_json}
"""

    payload = {
        "model": "mistralai/Mistral-7B-Instruct-v0.2:featherless-ai",
        "messages": [
            {
                "role": "system",
                "content": "You are an experienced technical hiring mentor."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.4,
        "max_tokens": 600
    }

    try:
        print("🚀 LLM DEBUG: Sending request to HF Router")

        response = requests.post(
            LLM_API_URL,
            headers=HEADERS,
            json=payload,
            timeout=60
        )

        print("📡 LLM DEBUG: Status Code =", response.status_code)
        print("📡 LLM DEBUG: Raw Response =", response.text)

        response.raise_for_status()
        data = response.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            print("❌ LLM DEBUG: Empty content from model")
            raise ValueError("Empty LLM response")

        print("✅ LLM DEBUG: Model responded successfully")

        # intro, bullets = format_guidance_for_html(content)
        sections = format_guidance_for_html(content)

        return {
            "text": content,
            "source": "llm",
            "sections": sections
        }

        # return {
        #     "text": content,
        #     "source": "llm",
        #     "intro": intro,
        #     "bullets": bullets
        # }

    except Exception as e:
        print("🔥 LLM ERROR:", str(e))
        fallback_text = fallback_mentor_guidance(analysis_json)
        intro, bullets = format_guidance_for_html(fallback_text)
        return {
            "text": fallback_text,
            "source": "rule_based",
            "intro": intro,
            "bullets": bullets
        }
