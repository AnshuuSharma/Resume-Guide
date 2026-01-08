import re
import spacy
from sentence_transformers import SentenceTransformer, util

# -------------------- MODELS --------------------
nlp = spacy.load("en_core_web_sm")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# -------------------- CONSTANTS --------------------
DEGREE_KEYWORDS = [
    "b.tech", "b.e", "bachelor", "m.tech", "m.e", "master",
    "b.sc", "m.sc", "phd"
]

SKILLS = [
    "python", "java", "c++", "sql", "machine learning",
    "deep learning", "nlp", "data science",
    "tensorflow", "pytorch", "flask", "fastapi",
    "docker", "aws", "git"
]

# -------------------- BASIC NLP UTILS --------------------
def split_sentences(text):
    doc = nlp(text)
    return [s.text.strip() for s in doc.sents if len(s.text.strip()) > 5]


def semantic_similarity(text1, text2):
    emb = embed_model.encode([text1, text2], convert_to_tensor=True)
    return util.cos_sim(emb[0], emb[1]).item()


# -------------------- EDUCATION --------------------
def detect_education_status(resume_text):
    lines = resume_text.lower().splitlines()
    edu_entries = []

    year_pattern = re.compile(r"(19|20)\d{2}\s*[-–]\s*(19|20)\d{2}")

    for line in lines:
        for deg in DEGREE_KEYWORDS:
            if deg in line:
                years = year_pattern.search(line)
                edu_entries.append({
                    "degree": deg,
                    "line": line.strip(),
                    "duration": years.group() if years else None
                })

    return edu_entries


def detect_jd_education_requirement(jd_text):
    jd_text = jd_text.lower()
    for deg in DEGREE_KEYWORDS:
        if deg in jd_text:
            return deg
    return None


def education_match(resume_edu, jd_req):
    if not jd_req:
        return "not_required"
    for edu in resume_edu:
        if jd_req in edu["degree"]:
            return "matched"
    return "missing"


# -------------------- EXPERIENCE --------------------
def parse_jd_experience_requirements(jd_text):
    exp_pattern = re.findall(r"(\d+)\+?\s+years?", jd_text.lower())
    return max(map(int, exp_pattern)) if exp_pattern else None


def extract_resume_domain_experience(resume_text):
    domains = []
    for skill in ["ml", "machine learning", "nlp", "backend", "frontend", "data"]:
        if skill in resume_text.lower():
            domains.append(skill)
    return list(set(domains))


def extract_role_based_experience(resume_text):
    roles = []
    for role in ["intern", "engineer", "developer", "analyst"]:
        if role in resume_text.lower():
            roles.append(role)
    return list(set(roles))

           
# -------------------- PROJECTS --------------------
def has_projects(resume_text):
    project_keywords = ["project", "built", "developed", "implemented"]
    return any(k in resume_text.lower() for k in project_keywords)


# -------------------- EXTRA CURRICULAR --------------------
def extract_extra_curriculars(resume_text):
    extras = []
    for word in ["hackathon", "volunteer", "open source", "club"]:
        if word in resume_text.lower():
            extras.append(word)
    return extras


# -------------------- NLP SKILL ANALYSIS --------------------
def semantic_skill_match(jd_text, resume_text, threshold=0.6):
    jd_sents = split_sentences(jd_text)
    res_sents = split_sentences(resume_text)

    skill_analysis = {}

    for skill in SKILLS:
        best_score = 0.0

        for jd in jd_sents:
            if skill not in jd.lower():
                continue
            for res in res_sents:
                score = semantic_similarity(jd, res)
                best_score = max(best_score, score)

        if best_score >= threshold:
            skill_analysis[skill] = {
                "status": "matched",
                "match_type": "semantic",
                "similarity": round(best_score, 3)
            }
        else:
            skill_analysis[skill] = {
                "status": "missing",
                "match_type": "none",
                "similarity": round(best_score, 3)
            }

    return skill_analysis


# -------------------- OVERALL JD ↔ RESUME ALIGNMENT --------------------
def overall_semantic_alignment(jd_text, resume_text):
    jd_sents = split_sentences(jd_text)
    res_sents = split_sentences(resume_text)

    scores = []
    for jd in jd_sents:
        best = max(
            semantic_similarity(jd, res)
            for res in res_sents
        )
        scores.append(best)

    return {
        "average_similarity": round(sum(scores) / len(scores), 3),
        "min_similarity": round(min(scores), 3),
        "max_similarity": round(max(scores), 3)
    }


# -------------------- FINAL JSON BUILDER --------------------
def build_analysis_json(jd_text, resume_text):
    resume_edu = detect_education_status(resume_text)
    jd_edu_req = detect_jd_education_requirement(jd_text)

    return {
        "education": {
            "resume": resume_edu,
            "jd_requirement": jd_edu_req,
            "match": education_match(resume_edu, jd_edu_req)
        },
        "experience": {
            "jd_required_years": parse_jd_experience_requirements(jd_text),
            "resume_roles": extract_role_based_experience(resume_text),
            "resume_domains": extract_resume_domain_experience(resume_text)
        },
        "projects": {
            "has_projects": has_projects(resume_text)
        },
        "skills": {
            "semantic_skill_analysis": semantic_skill_match(jd_text, resume_text)
        },
        "extras": extract_extra_curriculars(resume_text),
        "semantic_alignment": overall_semantic_alignment(jd_text, resume_text)
    }
