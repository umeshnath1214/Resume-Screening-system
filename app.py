from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os, hashlib, json
from utils.db import get_db, init_db
from utils.parser import extract_text_from_file
from utils.nlp import compute_match_score, extract_skills

app = Flask(__name__)
app.secret_key = 'your_secret_key_change_in_production'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ─── Auth Routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_password(request.form['password'])
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username=? AND password=?', (username, password)
        ).fetchone()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_password(request.form['password'])
        role = request.form.get('role', 'recruiter')
        db = get_db()
        try:
            db.execute('INSERT INTO users (username, password, role) VALUES (?,?,?)',
                       (username, password, role))
            db.commit()
            flash('Account created! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception:
            flash('Username already exists.', 'error')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    total_candidates = db.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]
    total_jobs = db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
    avg_score = db.execute('SELECT AVG(match_score) FROM candidates WHERE match_score > 0').fetchone()[0]
    top_candidates = db.execute(
        'SELECT c.name, c.email, c.match_score, j.job_title FROM candidates c '
        'LEFT JOIN jobs j ON c.job_id = j.id ORDER BY c.match_score DESC LIMIT 5'
    ).fetchall()
    return render_template('dashboard.html',
        total_candidates=total_candidates,
        total_jobs=total_jobs,
        avg_score=round(avg_score or 0, 1),
        top_candidates=top_candidates
    )

# ─── Jobs ─────────────────────────────────────────────────────────────────────

@app.route('/jobs', methods=['GET', 'POST'])
def jobs():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    if request.method == 'POST':
        job_title = request.form['job_title']
        required_skills = request.form['required_skills']
        description = request.form['description']
        db.execute('INSERT INTO jobs (job_title, required_skills, description) VALUES (?,?,?)',
                   (job_title, required_skills, description))
        db.commit()
        flash('Job added successfully!', 'success')
    all_jobs = db.execute('SELECT * FROM jobs ORDER BY id DESC').fetchall()
    return render_template('jobs.html', jobs=all_jobs)

@app.route('/jobs/delete/<int:job_id>')
def delete_job(job_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM jobs WHERE id=?', (job_id,))
    db.commit()
    flash('Job deleted.', 'success')
    return redirect(url_for('jobs'))

# ─── Upload Resume ────────────────────────────────────────────────────────────

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    all_jobs = db.execute('SELECT * FROM jobs').fetchall()
    if request.method == 'POST':
        name = request.form['candidate_name']
        email = request.form['candidate_email']
        job_id = request.form['job_id']
        file = request.files.get('resume')
        if not file or file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash('Only PDF, DOC, DOCX files are allowed.', 'error')
            return redirect(request.url)
        filename = f"{email}_{file.filename}".replace(' ', '_')
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        # Extract text
        resume_text = extract_text_from_file(filepath)
        # NLP matching
        job = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        score = 0
        if job:
            score = compute_match_score(resume_text, job['required_skills'] + ' ' + job['description'])
        skills_found = json.dumps(extract_skills(resume_text))
        db.execute(
            'INSERT INTO candidates (name, email, resume_text, match_score, job_id, skills_found, filename) VALUES (?,?,?,?,?,?,?)',
            (name, email, resume_text, score, job_id, skills_found, filename)
        )
        db.commit()
        flash(f'Resume uploaded! Match Score: {score:.1f}%', 'success')
        return redirect(url_for('results'))
    return render_template('upload.html', jobs=all_jobs)

# ─── Results & Ranking ────────────────────────────────────────────────────────

@app.route('/results')
def results():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    job_id = request.args.get('job_id', '')
    all_jobs = db.execute('SELECT * FROM jobs').fetchall()
    if job_id:
        candidates = db.execute(
            'SELECT c.*, j.job_title FROM candidates c LEFT JOIN jobs j ON c.job_id=j.id '
            'WHERE c.job_id=? ORDER BY c.match_score DESC', (job_id,)
        ).fetchall()
    else:
        candidates = db.execute(
            'SELECT c.*, j.job_title FROM candidates c LEFT JOIN jobs j ON c.job_id=j.id '
            'ORDER BY c.match_score DESC'
        ).fetchall()
    return render_template('results.html', candidates=candidates, jobs=all_jobs, selected_job=job_id)

@app.route('/candidate/<int:cid>')
def candidate_detail(cid):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    candidate = db.execute(
        'SELECT c.*, j.job_title, j.required_skills FROM candidates c '
        'LEFT JOIN jobs j ON c.job_id=j.id WHERE c.id=?', (cid,)
    ).fetchone()
    if not candidate:
        flash('Candidate not found.', 'error')
        return redirect(url_for('results'))
    skills = json.loads(candidate['skills_found']) if candidate['skills_found'] else []
    return render_template('candidate_detail.html', candidate=candidate, skills=skills)

@app.route('/candidate/delete/<int:cid>')
def delete_candidate(cid):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM candidates WHERE id=?', (cid,))
    db.commit()
    flash('Candidate removed.', 'success')
    return redirect(url_for('results'))

# ─── API for charts ───────────────────────────────────────────────────────────

@app.route('/api/score_distribution')
def score_distribution():
    if 'user_id' not in session:
        return jsonify([])
    db = get_db()
    rows = db.execute('SELECT match_score FROM candidates WHERE match_score > 0').fetchall()
    buckets = {'0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0}
    for r in rows:
        s = r['match_score']
        if s <= 20: buckets['0-20'] += 1
        elif s <= 40: buckets['21-40'] += 1
        elif s <= 60: buckets['41-60'] += 1
        elif s <= 80: buckets['61-80'] += 1
        else: buckets['81-100'] += 1
    return jsonify(buckets)

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    with app.app_context():
        init_db()
    app.run(debug=True)
