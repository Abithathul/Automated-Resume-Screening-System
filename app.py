from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import PyPDF2
import docx
import sqlite3
import re
import smtplib
from email.mime.text import MIMEText

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
CORS(app)

# -----------------------------
# CONFIG
# -----------------------------
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"pdf", "docx"}
DATABASE = "database.db"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# -----------------------------
# JOB DATA
# -----------------------------
JOB_DATA = {
    "ios developer": {
        "description": (
            "Responsible for designing, developing, and maintaining iOS applications using "
            "Swift and Objective-C. Work with RESTful APIs, UIKit, Core Data, and third-party libraries. "
            "Ensure app performance, quality, and responsiveness."
        ),
        "keywords": ["swift", "objective-c", "ios", "xcode", "uikit", "rest api", "core data", "mobile apps"],
        "experience": "0-3 years",
        "academic": "Bachelor's degree in CS or related"
    },
    "full stack developer": {
        "description": (
            "Develop end-to-end web applications including frontend (React, Angular) "
            "and backend (Node.js, Django, Spring Boot). Work with relational and NoSQL databases, "
            "REST APIs, and cloud deployment."
        ),
        "keywords": ["javascript", "react", "angular", "node.js", "django", "spring boot", "sql", "mongodb", "rest api"],
        "experience": "0-3 years",
        "academic": "Bachelor's degree in CS or related"
    },
    "java developer": {
        "description": (
            "Build scalable backend systems using Java, Spring Boot, Hibernate, and microservices architecture. "
            "Design APIs and optimize database queries."
        ),
        "keywords": ["java", "spring", "spring boot", "hibernate", "microservices", "rest api", "backend"],
        "experience": "0-3 years",
        "academic": "Bachelor's degree in CS or related"
    },
    "network administrator": {
        "description": (
            "Manage and maintain network infrastructure including routers, switches, firewalls, "
            "and DNS servers. Monitor network performance and troubleshoot connectivity issues."
        ),
        "keywords": ["network", "tcp/ip", "dns", "firewall", "routers", "switches", "network monitoring"],
        "experience": "0-3 years",
        "academic": "Bachelor's degree in IT, Networking, or related"
    },
    "software engineer": {
        "description": (
            "Design, develop, test, and maintain software systems and backend services. "
            "Work with APIs, databases, and implement scalable solutions."
        ),
        "keywords": ["software development", "backend", "api", "database", "system design", "cloud"],
        "experience": "0-3 years",
        "academic": "Bachelor's degree in CS or related"
    },
    "digital marketing": {
        "description": (
            "Develop and execute digital marketing strategies across SEO, SEM, social media, "
            "email campaigns, and content marketing. Analyze campaign performance using Google Analytics and Ads."
        ),
        "keywords": ["seo", "sem", "social media", "content marketing", "google ads", "meta ads", "analytics"],
        "experience": "0-2 years",
        "academic": "Bachelor's degree in Marketing, Business, or related"
    },
    "data scientist": {
        "description": (
            "Analyze complex datasets using Python, R, or SQL. Build machine learning models, "
            "perform statistical analysis, and provide data-driven insights for business decisions."
        ),
        "keywords": ["python", "r", "pandas", "numpy", "scikit-learn", "machine learning", "statistics", "data analysis", "sql"],
        "experience": "0-3 years",
        "academic": "Bachelor's or Master's degree in CS, Statistics, Mathematics, or related"
    }
}

# -----------------------------
# DATABASE
# -----------------------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_name TEXT,
        role TEXT,
        match_percentage REAL,
        final_score REAL,
        status TEXT,
        file_url TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# UTIL FUNCTIONS
# -----------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text(path):
    text = ""
    if path.endswith(".pdf"):
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                if page.extract_text():
                    text += page.extract_text()
    elif path.endswith(".docx"):
        doc = docx.Document(path)
        for para in doc.paragraphs:
            text += para.text
    return text.lower()
def extract_email(text):
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}", text)
    return match.group(0) if match else None


def send_email(receiver, status):
    sender = "kabinaya700@gmail.com"
    password = "zvhfdpnndcjzwmaq"

    if status == "Selected":
        message = "Congratulations! 🎉 You have been selected by Matics Technology. We are pleased to invite you for a face-to-face interview. Our team will contact you shortly with further details."
    elif status == "Shortlisted":
        message =  "Good news! 👍 You have been shortlisted by Matics Technology for the next stage of the selection process. We would like to invite you for a face-to-face interview. Further details will be shared soon."
    else:
        message =  "Thank you for your interest in Matics Technology.After careful consideration, we regret to inform you that you have not been selected for this position.We wish you all the best for your future endeavors."

    msg = MIMEText(message)
    msg['Subject'] = "Interview Result"
    msg['From'] = sender
    msg['To'] = receiver

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        print("Email sent to:", receiver)
    except Exception as e:
        print("Email error:", e)

# -----------------------------
# ACADEMIC CHECK
# -----------------------------
def extract_academic_percentage(text):
    perc_match = re.search(r'(\d{2,3}(?:\.\d+)?)\s*%', text)
    if perc_match:
        return float(perc_match.group(1))
    cgpa_match = re.search(r'(\d(?:\.\d+)?)\s*/\s*10', text)
    if cgpa_match:
        return float(cgpa_match.group(1)) * 10
    cgpa2_match = re.search(r'(\d(?:\.\d+)?)\s*cgpa', text)
    if cgpa2_match:
        return float(cgpa2_match.group(1)) * 10
    return 0

# -----------------------------
# EXPERIENCE
# -----------------------------
def extract_experience(text):
    patterns = [r'(\d+)\+?\s*years', r'(\d+)\s*yrs', r'(\d+)\s*year experience']
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return 0

# -----------------------------
# INTERNSHIP
# -----------------------------
def detect_internship(text):
    internship_words = ["intern", "internship", "trainee"]
    return any(word in text for word in internship_words)

# -----------------------------
# PROJECTS
# -----------------------------
def extract_projects(text):
    project_words = ["project", "developed", "built", "created"]
    return sum(1 for word in project_words if word in text)

# -----------------------------
# MATCHING
# -----------------------------
def calculate_match(resume, job_role):
    resume = resume.lower()
    if job_role in JOB_DATA:
        job_text = JOB_DATA[job_role]["description"].lower()
        keywords = set(k.lower() for k in JOB_DATA[job_role]["keywords"])
    else:
        job_text = job_role.lower()
        keywords = set()

    tfidf = TfidfVectorizer(stop_words="english")
    matrix = tfidf.fit_transform([resume, job_text])
    similarity_score = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]

    # Count each keyword only once
    keyword_hits = sum(1 for k in keywords if k in resume)
    final_match = round(min((similarity_score * 100) + (keyword_hits * 5), 100), 2)
    return final_match

def analyze_candidate(text):
    all_keywords = set(k.lower() for r in JOB_DATA.values() for k in r["keywords"])
    hits = sum(1 for k in all_keywords if k in text)
    core = hits // 3
    add = hits // 5
    return core, add

# -----------------------------
# STATUS PREDICTION
# -----------------------------
def predict_status(final_score, experience, job_role):
    required_exp = 0
    if job_role in JOB_DATA:
        exp_text = JOB_DATA[job_role]["experience"]
        exp_match = re.search(r'\d+', exp_text)
        if exp_match:
            required_exp = int(exp_match.group())

    if final_score >= 70 and experience >= required_exp:
        return "Selected"
    elif final_score >= 60:
        return "Shortlisted"
    else:
        return "Rejected"

# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def login():
    return render_template("Login.html")

@app.route("/login", methods=["POST"])
def handle_login():
    username = request.form.get("username")
    password = request.form.get("password")
    if username == "admin" and password == "123456":
        return redirect(url_for("index"))
    return "Invalid Username or Password"

@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/resumes")
def resumes():
    return render_template("resumes.html")

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# -----------------------------
# API
# -----------------------------
@app.route("/get_candidates")
def get_candidates():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM candidates").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route("/clear_candidates", methods=["POST"])
def clear_candidates():
    conn = get_db_connection()
    conn.execute("DELETE FROM candidates")
    conn.commit()
    conn.close()
    return jsonify({"message": "All cleared"})

@app.route("/delete_candidate/<int:id>", methods=["DELETE"])
def delete_candidate(id):
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM candidates WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    if cursor.rowcount == 0:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"message": "Deleted"})

# -----------------------------
# UPLOAD
# -----------------------------
@app.route("/upload", methods=["POST"])
def upload_resume():
    file = request.files.get("resume")
    job_role = request.form.get("job_role", "").lower()

    if not file:
        return jsonify({"error": "No file"}), 400
    if not job_role:
        return jsonify({"error": "Select role"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF/DOCX"}), 400

    filename = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)

    text = extract_text(path)
    email = extract_email(text)

    # FEATURES
    match = calculate_match(text, job_role)
    experience = extract_experience(text)
    has_internship = detect_internship(text)
    project_count = extract_projects(text)
    core, add = analyze_candidate(text)

    intern_score = 10 if has_internship else 0
    project_score = project_count * 5

    # FINAL SCORE
    final_score = min(
        (match * 0.4) +
        (core * 10) +
        (add * 5) +
        (experience * 5) +
        intern_score +
        project_score,
        100
    )
    final_score = int(round(final_score))

    # STATUS
    status = predict_status(final_score, experience, job_role)

    name = os.path.splitext(file.filename)[0]
    role = job_role.title()
    file_url = f"http://localhost:5000/uploads/{filename}"

    conn = get_db_connection()
    conn.execute("""
    INSERT INTO candidates (candidate_name, role, match_percentage, final_score, status, file_url)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (name, role, match, final_score, status, file_url))
    conn.commit()
    conn.close()
    if email:
     send_email(email, status)

    return jsonify({
        "candidate_name": name,
        "role": role,
        "match_percentage": match,
        "final_score": final_score,
        "status": status,
        "experience": experience,
        "internship": has_internship,
        "projects": project_count,
        "file_url": file_url
    })

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
