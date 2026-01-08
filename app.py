import os
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
import PyPDF2
from dotenv import load_dotenv
from utils.text_cleaning import clean_text
from Service_files.nlp_analysis import build_analysis_json
from Service_files.llm_guidance import generate_resume_guidance

# -------------------- CONFIG --------------------

load_dotenv()

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------- HELPERS --------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text


# -------------------- ROUTES --------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    job_desc = request.form.get("job_description")
    resume_file = request.files.get("resume")

    if not job_desc or not resume_file:
        return render_template("index.html", error="Please provide both JD and resume")

    if not allowed_file(resume_file.filename):
        return render_template("index.html", error="Only PDF resumes are allowed")

    # ---- Save Resume ----
    filename = secure_filename(resume_file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    resume_file.save(file_path)

    # ---- Extract & Clean ----
    resume_text = extract_text_from_pdf(file_path)

    jd_clean = clean_text(job_desc)
    resume_clean = clean_text(resume_text)

    # ---- NLP Analysis ----
    analysis_json = build_analysis_json(jd_clean, resume_clean)

    # ---- LLM Guidance ----
    guidance = generate_resume_guidance(analysis_json)
    

    return render_template(
        "result.html",
        sections=guidance["sections"]
)

if __name__ == "__main__":
 port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
