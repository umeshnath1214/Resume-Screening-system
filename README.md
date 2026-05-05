# AI-Powered Resume Screening System
### BCA 6th Semester Major Project — Umesh Nath (UU2309000385)
### Mentor: Dr. Monisha Awasthi | Uttaranchal University

---

## Project Overview
An intelligent web application that screens resumes using NLP (TF-IDF + Cosine Similarity)
and ranks candidates based on their match with job descriptions.

## Tech Stack
- **Backend:** Python 3.8+, Flask
- **NLP:** Custom TF-IDF + Cosine Similarity (no heavy ML library required)
- **Database:** SQLite (easy to switch to MySQL)
- **PDF Parsing:** pdfplumber, pypdf
- **DOCX Parsing:** python-docx
- **Frontend:** HTML5, CSS3, JavaScript, Chart.js

## Project Structure
```
resume_screening/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── resume_screening.db     # SQLite database (auto-created)
├── uploads/                # Uploaded resume files
├── utils/
│   ├── db.py               # Database connection & init
│   ├── parser.py           # Resume text extraction (PDF/DOCX)
│   └── nlp.py              # NLP: tokenize, TF-IDF, cosine similarity
└── templates/
    ├── base.html           # Base layout with sidebar
    ├── login.html          # Login page
    ├── register.html       # Register page
    ├── dashboard.html      # Dashboard with stats & charts
    ├── jobs.html           # Job management
    ├── upload.html         # Resume upload form
    ├── results.html        # Candidate rankings
    └── candidate_detail.html  # Individual candidate profile
```

## Setup & Run

### Step 1: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run the Application
```bash
python app.py
```

### Step 3: Open in Browser
```
http://127.0.0.1:5000
```

### Default Login
```
Username: admin
Password: admin123
```

## How the NLP Works

1. **Text Extraction** — Resume file (PDF/DOCX) → raw text using pdfplumber/python-docx
2. **Tokenization** — Text split into words, stop words removed
3. **TF-IDF Vectorization** — Term Frequency for resume and job description
4. **Cosine Similarity** — Angle between two text vectors = similarity score
5. **Skill Boost** — 40% weight given to known skill keyword overlap
6. **Final Score** — 0–100% match score, candidates ranked highest to lowest

## Modules
| Module | File | Description |
|--------|------|-------------|
| Auth | app.py | Login, register, session, SHA-256 hashing |
| Resume Upload | app.py + utils/parser.py | File upload, text extraction |
| NLP Processing | utils/nlp.py | Tokenize, TF-IDF, cosine similarity |
| Job Management | app.py | CRUD for job openings |
| Matching & Scoring | utils/nlp.py | compute_match_score() |
| Ranking | app.py /results | ORDER BY match_score DESC |
| Dashboard | app.py + dashboard.html | Stats + Chart.js bar chart |

## To Use MySQL Instead of SQLite
In `utils/db.py`, replace the SQLite connection with:
```python
import mysql.connector
conn = mysql.connector.connect(host='localhost', user='root', password='', database='resume_db')
```
And adjust the SQL syntax accordingly (use %s instead of ?).

## Security Features
- SHA-256 password hashing
- Session-based authentication
- File type validation (PDF/DOC/DOCX only)
- File size limit (5MB)
- SQL parameterized queries (injection-safe)
