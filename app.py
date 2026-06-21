from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import mysql.connector
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from modules.resume_parser import extract_text_from_file
from modules.nlp_processor import process_text, extract_skills
from modules.matching_engine import compute_match_score
from modules.ranking import rank_candidates
from modules.report_generator import generate_report
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ✅ FIX: Register custom from_json filter for Jinja2 templates
app.jinja_env.filters['from_json'] = json.loads

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

def get_db():
    return mysql.connector.connect(
        host="localhost", user="root", password="Umesh@123", database="resume_screening_db"
    )

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db(); cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone(); db.close()
        if user and check_password_hash(user['password'], password):
            session.update({'user_id': user['id'], 'username': user['username'], 'role': user['role']})
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        db = get_db(); cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, email, role) VALUES (%s,%s,%s,%s)",
                (request.form['username'], generate_password_hash(request.form['password']),
                 request.form['email'], request.form.get('role', 'recruiter')))
            db.commit(); flash('Registration successful!', 'success'); return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Username or email already exists.', 'danger')
        finally:
            db.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear(); flash('Logged out.', 'info'); return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS total FROM candidates")
    total_candidates = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) AS total FROM jobs")
    total_jobs = cursor.fetchone()['total']
    cursor.execute("""SELECT c.name, c.match_score, j.title AS job_title
        FROM candidates c JOIN jobs j ON c.job_id = j.id ORDER BY c.match_score DESC LIMIT 5""")
    top_candidates = cursor.fetchall(); db.close()
    return render_template('dashboard.html', total_candidates=total_candidates,
                           total_jobs=total_jobs, top_candidates=top_candidates)

@app.route('/jobs', methods=['GET', 'POST'])
def jobs():
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db(); cursor = db.cursor(dictionary=True)
    if request.method == 'POST':
        cursor.execute("INSERT INTO jobs (title, description, skills_required, created_by) VALUES (%s,%s,%s,%s)",
            (request.form['title'], request.form['description'], request.form['skills_required'], session['user_id']))
        db.commit(); flash('Job added!', 'success')
    cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
    all_jobs = cursor.fetchall(); db.close()
    return render_template('jobs.html', jobs=all_jobs)

@app.route('/jobs/delete/<int:job_id>')
def delete_job(job_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db(); cursor = db.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = %s", (job_id,)); db.commit(); db.close()
    flash('Job deleted.', 'info'); return redirect(url_for('jobs'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM jobs"); all_jobs = cursor.fetchall()
    if request.method == 'POST':
        job_id = request.form['job_id']; files = request.files.getlist('resumes')
        cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,)); job = cursor.fetchone()
        if not job: flash('Invalid job.', 'danger'); return redirect(url_for('upload'))
        processed = 0
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                raw_text = extract_text_from_file(filepath)
                processed_text = process_text(raw_text)
                skills = extract_skills(processed_text)
                score = compute_match_score(processed_text, process_text(job['description'] + ' ' + job['skills_required']))
                candidate_name = filename.rsplit('.', 1)[0].replace('_', ' ').title()
                cursor.execute("""INSERT INTO candidates (name, resume_filename, extracted_text, skills, match_score, job_id)
                    VALUES (%s,%s,%s,%s,%s,%s)""",
                    (candidate_name, filename, processed_text[:5000], json.dumps(skills), round(score * 100, 2), job_id))
                db.commit(); processed += 1
        flash(f'{processed} resume(s) processed!', 'success'); db.close()
        return redirect(url_for('results', job_id=job_id))
    db.close()
    return render_template('upload.html', jobs=all_jobs)

@app.route('/results/<int:job_id>')
def results(job_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,)); job = cursor.fetchone()
    cursor.execute("SELECT * FROM candidates WHERE job_id = %s ORDER BY match_score DESC", (job_id,))
    candidates = cursor.fetchall()
    # ✅ FIX: Parse skills JSON in Python before passing to template (extra safety)
    for c in candidates:
        if c.get('skills') and isinstance(c['skills'], str):
            try:
                c['skills'] = json.loads(c['skills'])
            except (json.JSONDecodeError, TypeError):
                c['skills'] = []
    db.close()
    return render_template('results.html', job=job, candidates=rank_candidates(candidates))

@app.route('/results')
def all_results():
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("""SELECT c.*, j.title AS job_title FROM candidates c
        JOIN jobs j ON c.job_id = j.id ORDER BY c.match_score DESC""")
    candidates = cursor.fetchall()
    # ✅ FIX: Parse skills JSON in Python before passing to template
    for c in candidates:
        if c.get('skills') and isinstance(c['skills'], str):
            try:
                c['skills'] = json.loads(c['skills'])
            except (json.JSONDecodeError, TypeError):
                c['skills'] = []
    db.close()
    return render_template('all_results.html', candidates=candidates)

@app.route('/report/<int:job_id>')
def report(job_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,)); job = cursor.fetchone()
    cursor.execute("SELECT * FROM candidates WHERE job_id = %s ORDER BY match_score DESC", (job_id,))
    candidates = cursor.fetchall(); db.close()
    return render_template('report.html', report=generate_report(job, candidates), job=job)

@app.route('/candidate/<int:candidate_id>')
def candidate_detail(candidate_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("""SELECT c.*, j.title AS job_title, j.skills_required
        FROM candidates c JOIN jobs j ON c.job_id = j.id WHERE c.id = %s""", (candidate_id,))
    candidate = cursor.fetchone(); db.close()
    if candidate and candidate['skills']:
        candidate['skills'] = json.loads(candidate['skills'])
    return render_template('candidate_detail.html', candidate=candidate)

@app.route('/api/scores/<int:job_id>')
def api_scores(job_id):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT name, match_score FROM candidates WHERE job_id = %s ORDER BY match_score DESC", (job_id,))
    data = cursor.fetchall(); db.close()
    return jsonify(data)

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
