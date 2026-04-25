"""
AcmeStaff Pro — Staffing Platform
===================================
A modern staffing and recruitment platform.
"""

import os
import sqlite3
import hashlib
import subprocess
from flask import (
    Flask, request, render_template_string, redirect,
    url_for, session, g, jsonify, send_from_directory,
    make_response
)

app = Flask(__name__)
app.secret_key = "super_secret_key_12345"
app.config['DEBUG'] = True
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['DATABASE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'staffing.db')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# ── Database ──────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(app.config['DATABASE'])
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            ssn TEXT,
            address TEXT,
            role TEXT DEFAULT 'applicant',
            bio TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            description TEXT,
            requirements TEXT,
            salary TEXT,
            location TEXT,
            job_type TEXT DEFAULT 'full-time',
            posted_by INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            user_id INTEGER,
            cover_letter TEXT,
            resume_path TEXT,
            status TEXT DEFAULT 'pending',
            reviewer_notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER,
            author_id INTEGER,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            subject TEXT,
            body TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    users = [
        ('admin', hashlib.md5(b'admin123').hexdigest(), 'admin@acmestaffing.com', '555-0100', '123-45-6789', '100 Corp Blvd, Suite 1', 'admin', 'Platform administrator'),
        ('sarah_r', hashlib.md5(b'recruit2024').hexdigest(), 'sarah.jones@acmestaffing.com', '555-0101', '234-56-7890', '200 HR Lane', 'recruiter', 'Senior recruiter, 10 years experience'),
        ('mike_r', hashlib.md5(b'hiring99').hexdigest(), 'mike.chen@acmestaffing.com', '555-0104', '567-89-0123', '200 HR Lane', 'recruiter', 'Tech recruiter specializing in engineering roles'),
        ('jdoe', hashlib.md5(b'password').hexdigest(), 'john.doe@email.com', '555-0102', '345-67-8901', '42 Elm Street, Apt 3B', 'applicant', 'Full-stack developer, 5 years exp'),
        ('jsmith', hashlib.md5(b'letmein').hexdigest(), 'jane.smith@email.com', '555-0103', '456-78-9012', '88 Oak Avenue', 'applicant', 'Data analyst with ML background'),
        ('bob_dev', hashlib.md5(b'bob2024').hexdigest(), 'bob.wilson@email.com', '555-0105', '678-90-1234', '15 Pine Road', 'applicant', 'DevOps engineer, AWS certified'),
    ]
    for u in users:
        try:
            db.execute('INSERT INTO users (username, password, email, phone, ssn, address, role, bio) VALUES (?,?,?,?,?,?,?,?)', u)
        except sqlite3.IntegrityError:
            pass

    jobs = [
        ('Senior Python Developer', 'TechCorp Inc.', 'Looking for experienced Python dev. Must know Flask, Django, FastAPI. Remote-first team building next-gen SaaS.', 'Python 5+ years, REST APIs, PostgreSQL, Docker', '$120,000 - $160,000', 'Remote', 'full-time', 1),
        ('Data Analyst', 'DataDriven LLC', 'SQL, Python, Tableau. Join our analytics team crunching numbers for Fortune 500 clients.', 'SQL expert, Python, Tableau/PowerBI, statistics background', '$85,000 - $110,000', 'New York, NY', 'full-time', 1),
        ('DevOps Engineer', 'CloudScale Systems', 'K8s, AWS, Terraform. Build and maintain CI/CD pipelines for microservices architecture.', 'AWS/GCP, Kubernetes, Terraform, Jenkins/GitHub Actions', '$130,000 - $170,000', 'San Francisco, CA', 'full-time', 2),
        ('Frontend Developer', 'PixelPerfect Studios', 'React, TypeScript, CSS wizardry. Build beautiful, accessible UIs for millions of users.', 'React 3+ years, TypeScript, CSS/Tailwind, accessibility', '$100,000 - $140,000', 'Austin, TX', 'hybrid', 2),
        ('Security Engineer', 'SafeGuard Corp', 'Pen testing, SAST/DAST, incident response. Protect critical infrastructure.', 'OSCP/CEH preferred, Python scripting, cloud security', '$140,000 - $180,000', 'Washington, DC', 'on-site', 1),
        ('Junior Backend Developer', 'StartupXYZ', 'Entry level Flask/Django role. Great mentorship, fast growth.', 'CS degree or bootcamp, Python basics, eagerness to learn', '$65,000 - $85,000', 'Denver, CO', 'remote', 3),
        ('QA Automation Engineer', 'QualityFirst Inc.', 'Selenium, Cypress, API testing. Build test frameworks from scratch.', 'Selenium/Cypress, Python/JS, CI/CD integration', '$95,000 - $125,000', 'Chicago, IL', 'hybrid', 2),
        ('Machine Learning Engineer', 'AI Innovations', 'PyTorch, TensorFlow, MLOps. Deploy models at scale for NLP products.', 'MS/PhD in CS/ML, PyTorch, MLflow, production ML experience', '$150,000 - $200,000', 'Seattle, WA', 'full-time', 1),
    ]
    for j in jobs:
        try:
            db.execute('INSERT INTO jobs (title, company, description, requirements, salary, location, job_type, posted_by) VALUES (?,?,?,?,?,?,?,?)', j)
        except:
            pass

    applications = [
        (1, 4, 'I am very excited about this Python role. I have 5 years of Flask experience and have built several production APIs.', None, 'pending', ''),
        (2, 5, 'My data analysis experience spans 5 years. Proficient in SQL, Python, and Tableau.', None, 'reviewed', 'Strong candidate, schedule interview'),
        (5, 4, 'Security is my passion. I hold OSCP and CEH certifications and have conducted numerous pen tests.', None, 'pending', ''),
        (3, 6, 'AWS certified with 3 years DevOps experience. Built CI/CD pipelines serving 100+ developers.', None, 'interviewed', 'Technical assessment passed'),
        (8, 5, 'Published 3 papers on NLP. Experience deploying transformer models at scale.', None, 'pending', ''),
        (4, 6, 'Self-taught React developer with a portfolio of 10+ projects. Passionate about accessibility.', None, 'reviewed', ''),
    ]
    for a in applications:
        try:
            db.execute('INSERT INTO applications (job_id, user_id, cover_letter, resume_path, status, reviewer_notes) VALUES (?,?,?,?,?,?)', a)
        except:
            pass

    messages = [
        (2, 4, 'Interview Invitation', 'Hi John, we would like to schedule an interview for the Senior Python Developer role. Please reply with your availability.', 0),
        (2, 5, 'Application Update', 'Hi Jane, your application for Data Analyst has been reviewed. We will be in touch soon.', 1),
        (1, 2, 'New Applicants', 'Sarah, we have 3 new applicants this week. Please review them at your earliest convenience.', 0),
        (3, 6, 'Technical Assessment', 'Bob, please complete the technical assessment at the link below within 48 hours.', 0),
    ]
    for m in messages:
        try:
            db.execute('INSERT INTO messages (sender_id, receiver_id, subject, body, is_read) VALUES (?,?,?,?,?)', m)
        except:
            pass

    db.commit()
    db.close()


# ── Base Template ─────────────────────────────────────────────

BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AcmeStaff Pro - {{ title }}</title>
    <style>
        :root {
            --bg: #0a0a0f; --bg2: #12121a; --card: #1a1a26; --card-h: #22222f;
            --red: #ff4d4d; --red-d: #cc3333; --red-g: rgba(255,77,77,0.15);
            --t1: #e8e8ed; --t2: #8888a0; --t3: #55556a; --brd: #2a2a3a;
            --grn: #22c55e; --ylw: #f59e0b; --blu: #3b82f6;
        }
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; background:var(--bg); color:var(--t1); min-height:100vh; font-size:14px; }
        a { color:var(--red); text-decoration:none; }
        a:hover { text-decoration:underline; }

        .nav { background:var(--bg2); border-bottom:1px solid var(--brd); padding:0 2rem; display:flex; align-items:center; justify-content:space-between; height:56px; position:sticky; top:0; z-index:100; }
        .nav-brand { font-weight:700; font-size:1.1rem; color:var(--red); letter-spacing:-0.5px; text-decoration:none; }
        .nav-brand span { color:var(--t3); font-weight:400; }
        .nav-links { display:flex; gap:4px; align-items:center; }
        .nav-links a { color:var(--t2); padding:6px 12px; border-radius:6px; font-size:13px; font-weight:500; text-decoration:none; }
        .nav-links a:hover { color:var(--t1); background:var(--card); }
        .nav-right { display:flex; align-items:center; gap:10px; font-size:13px; color:var(--t2); }
        .badge { font-size:10px; text-transform:uppercase; letter-spacing:1px; padding:2px 8px; border-radius:3px; background:var(--red-g); color:var(--red); border:1px solid rgba(255,77,77,0.2); font-weight:600; }
        .btn { display:inline-flex; align-items:center; gap:6px; padding:7px 16px; border-radius:6px; font-size:13px; font-weight:600; border:none; cursor:pointer; text-decoration:none; transition:all 0.15s; font-family:inherit; }
        .btn-red { background:var(--red); color:#fff; }
        .btn-red:hover { background:var(--red-d); text-decoration:none; }
        .btn-ghost { background:transparent; color:var(--t2); border:1px solid var(--brd); }
        .btn-ghost:hover { color:var(--t1); border-color:var(--t3); text-decoration:none; }
        .btn-sm { padding:4px 10px; font-size:12px; }
        .btn-grn { background:var(--grn); color:#fff; }

        .wrap { max-width:1100px; margin:0 auto; padding:2rem; }
        .page-hdr { margin-bottom:2rem; padding-bottom:1.5rem; border-bottom:1px solid var(--brd); }
        .page-hdr h1 { font-size:1.5rem; font-weight:700; margin-bottom:4px; }
        .page-hdr p { color:var(--t2); font-size:14px; }

        .card { background:var(--card); border:1px solid var(--brd); border-radius:10px; padding:1.5rem; margin-bottom:1rem; transition:all 0.15s; }
        .card:hover { background:var(--card-h); border-color:#3a3a4a; }
        .card h3 { font-size:1rem; margin-bottom:4px; }
        .meta { font-size:12px; color:var(--t2); display:flex; gap:14px; margin-bottom:10px; flex-wrap:wrap; }
        .card p { font-size:14px; color:var(--t2); line-height:1.6; }
        .salary { color:var(--grn); font-weight:700; font-size:13px; }
        .job-type { font-size:11px; padding:2px 8px; border-radius:10px; background:rgba(59,130,246,0.15); color:var(--blu); text-transform:uppercase; letter-spacing:0.5px; font-weight:600; }

        .form-group { margin-bottom:1.25rem; }
        .form-group label { display:block; font-size:12px; font-weight:600; color:var(--t2); margin-bottom:5px; text-transform:uppercase; letter-spacing:0.5px; }
        input[type="text"], input[type="password"], input[type="email"], input[type="file"], textarea, select {
            width:100%; padding:9px 12px; border-radius:6px; border:1px solid var(--brd); background:var(--bg); color:var(--t1); font-size:14px; font-family:inherit;
        }
        input:focus, textarea:focus, select:focus { outline:none; border-color:var(--red); box-shadow:0 0 0 3px var(--red-g); }
        textarea { min-height:100px; resize:vertical; }

        .alert { padding:12px 16px; border-radius:8px; font-size:13px; margin-bottom:1.5rem; border:1px solid; }
        .alert-err { background:rgba(239,68,68,0.1); border-color:rgba(239,68,68,0.2); color:#f87171; }
        .alert-ok { background:rgba(34,197,94,0.1); border-color:rgba(34,197,94,0.2); color:#4ade80; }
        .alert-warn { background:rgba(245,158,11,0.1); border-color:rgba(245,158,11,0.2); color:#fbbf24; }
        .alert-info { background:rgba(59,130,246,0.1); border-color:rgba(59,130,246,0.2); color:#60a5fa; }

        table { width:100%; border-collapse:collapse; }
        th { text-align:left; padding:8px 12px; font-size:11px; text-transform:uppercase; letter-spacing:1px; color:var(--t3); border-bottom:1px solid var(--brd); }
        td { padding:10px 12px; font-size:13px; border-bottom:1px solid rgba(42,42,58,0.5); }
        tr:hover td { background:rgba(255,255,255,0.02); }

        .status { font-size:11px; font-weight:600; padding:2px 8px; border-radius:20px; text-transform:uppercase; letter-spacing:0.5px; }
        .s-pending { background:rgba(245,158,11,0.15); color:#fbbf24; }
        .s-reviewed { background:rgba(59,130,246,0.15); color:#60a5fa; }
        .s-interviewed { background:rgba(168,85,247,0.15); color:#c084fc; }
        .s-accepted { background:rgba(34,197,94,0.15); color:#4ade80; }
        .s-rejected { background:rgba(239,68,68,0.15); color:#f87171; }

        .grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:1.5rem; }
        .comment { background:var(--bg); border-radius:8px; padding:12px; margin-top:10px; border-left:3px solid var(--red); }
        .comment .author { font-size:12px; color:var(--red); font-weight:600; margin-bottom:4px; }
        .comment .text { font-size:13px; color:var(--t2); }
        .msg-row { display:flex; justify-content:space-between; align-items:center; padding:12px 0; border-bottom:1px solid rgba(42,42,58,0.5); }
        .msg-row:hover { background:rgba(255,255,255,0.02); }
        .msg-unread { font-weight:700; }
        .msg-subject { font-size:14px; }
        .msg-from { font-size:12px; color:var(--t2); }
        .msg-date { font-size:11px; color:var(--t3); }
        .empty { text-align:center; padding:3rem; color:var(--t3); }
        .tabs { display:flex; gap:4px; margin-bottom:1.5rem; }
        .tabs a { padding:8px 16px; border-radius:6px; font-size:13px; font-weight:500; color:var(--t2); text-decoration:none; }
        .tabs a:hover, .tabs a.active { background:var(--card); color:var(--t1); }
        footer { text-align:center; padding:2rem; color:var(--t3); font-size:12px; border-top:1px solid var(--brd); margin-top:3rem; }
        @media (max-width:768px) { .grid-2 { grid-template-columns:1fr; } .nav { padding:0 1rem; } .wrap { padding:1rem; } }
    </style>
</head>
<body>
    <nav class="nav">
        <a href="/" class="nav-brand">AcmeStaff<span>Pro</span></a>
        <div class="nav-links">
            <a href="/jobs">Jobs</a>
            {% if session.get('user_id') %}
                <a href="/dashboard">Dashboard</a>
                <a href="/messages">Messages</a>
                <a href="/profile/{{ session.get('user_id') }}">Profile</a>
                <a href="/search">Search</a>
                <a href="/feedback">Feedback</a>
                {% if session.get('role') in ('admin', 'recruiter') %}
                    <a href="/admin">Admin</a>
                {% endif %}
            {% endif %}
        </div>
        <div class="nav-right">
            {% if session.get('user_id') %}
                <span class="badge">{{ session.get('role', 'user') }}</span>
                <span>{{ session.get('username', '') }}</span>
                <a href="/logout" class="btn btn-ghost btn-sm">Logout</a>
            {% else %}
                <a href="/login" class="btn btn-ghost btn-sm">Login</a>
                <a href="/register" class="btn btn-red btn-sm">Sign Up</a>
            {% endif %}
        </div>
    </nav>
    <div class="wrap">
        {% block content %}{% endblock %}
    </div>
    <footer>AcmeStaff Pro v2.1.0 — &copy; 2026 Acme Staffing Solutions</footer>
</body>
</html>
'''


# ── Helper ────────────────────────────────────────────────────

def render_page(title, content_html):
    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content_html)
    return render_template_string(template, title=title)


# ── Routes ────────────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    job_count = db.execute('SELECT COUNT(*) FROM jobs WHERE is_active = 1').fetchone()[0]
    user_count = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    return render_page("Home", f'''
        <div class="page-hdr">
            <h1>Find Your Next Opportunity</h1>
            <p>Connecting top talent with leading companies — {job_count} open positions, {user_count} registered professionals</p>
        </div>
        <div class="grid-2">
            <div class="card"><h3>Browse Jobs</h3><p>Explore open positions from top employers.</p><br><a href="/jobs" class="btn btn-red">View Listings</a></div>
            <div class="card"><h3>Quick Apply</h3><p>Upload your resume and apply instantly.</p><br><a href="/register" class="btn btn-ghost">Get Started</a></div>
        </div>
        <div class="card" style="margin-top:1rem;">
            <h3>For Recruiters</h3>
            <p>Post jobs, review applicants, and manage your hiring pipeline all in one place.</p>
            <br><a href="/login" class="btn btn-ghost btn-sm">Recruiter Login</a>
        </div>
    ''')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        hashed = hashlib.md5(password.encode()).hexdigest()
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{hashed}'"
        db = get_db()
        try:
            user = db.execute(query).fetchone()
            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['email'] = user['email']
                session['ssn'] = user['ssn']
                return redirect('/dashboard')
            else:
                error = "Invalid credentials"
        except Exception as e:
            error = f"Database error: {str(e)}"

    return render_page("Login", f'''
        <div style="max-width:400px; margin:0 auto;">
            <div class="page-hdr" style="text-align:center;"><h1>Sign In</h1><p>Access your AcmeStaff Pro account</p></div>
            {'<div class="alert alert-err">' + error + '</div>' if error else ''}
            <div class="card">
                <form method="POST">
                    <div class="form-group"><label>Username</label><input type="text" name="username" required></div>
                    <div class="form-group"><label>Password</label><input type="password" name="password" required></div>
                    <button type="submit" class="btn btn-red" style="width:100%;">Sign In</button>
                </form>
                <p style="text-align:center;margin-top:1rem;font-size:13px;color:var(--t3);">
                    <a href="/forgot-password">Forgot password?</a> · <a href="/register">Create account</a>
                </p>
            </div>
        </div>
    ''')


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        ssn = request.form.get('ssn', '')
        address = request.form.get('address', '')
        hashed = hashlib.md5(password.encode()).hexdigest()
        db = get_db()
        try:
            db.execute('INSERT INTO users (username, password, email, phone, ssn, address, role) VALUES (?,?,?,?,?,?,?)',
                       (username, hashed, email, phone, ssn, address, 'applicant'))
            db.commit()
            return redirect('/login')
        except sqlite3.IntegrityError:
            error = "Username already exists"
        except Exception as e:
            error = f"Error: {str(e)}"

    return render_page("Register", f'''
        <div style="max-width:480px; margin:0 auto;">
            <div class="page-hdr" style="text-align:center;"><h1>Create Account</h1><p>Join AcmeStaff Pro</p></div>
            {'<div class="alert alert-err">' + error + '</div>' if error else ''}
            <div class="card">
                <form method="POST">
                    <div class="grid-2">
                        <div class="form-group"><label>Username</label><input type="text" name="username" required></div>
                        <div class="form-group"><label>Password</label><input type="password" name="password" required></div>
                    </div>
                    <div class="form-group"><label>Email</label><input type="email" name="email" required></div>
                    <div class="grid-2">
                        <div class="form-group"><label>Phone</label><input type="text" name="phone"></div>
                        <div class="form-group"><label>Social Security Number</label><input type="text" name="ssn" placeholder="Required for background check"></div>
                    </div>
                    <div class="form-group"><label>Address</label><input type="text" name="address"></div>
                    <button type="submit" class="btn btn-red" style="width:100%;">Create Account</button>
                </form>
            </div>
        </div>
    ''')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    msg = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        db = get_db()
        user = db.execute(f"SELECT * FROM users WHERE username = '{username}'").fetchone()
        if user:
            import time
            token = hashlib.md5(f"{username}{time.time()}".encode()).hexdigest()
            db.execute('INSERT INTO password_reset_tokens (user_id, token) VALUES (?, ?)', (user['id'], token))
            db.commit()
            msg = f"Password reset link: /reset-password?token={token}"
        else:
            msg = f"No account found for username: {username}"

    return render_page("Forgot Password", f'''
        <div style="max-width:400px; margin:0 auto;">
            <div class="page-hdr" style="text-align:center;"><h1>Reset Password</h1><p>Enter your username to get a reset link</p></div>
            {'<div class="alert alert-info">' + msg + '</div>' if msg else ''}
            <div class="card">
                <form method="POST">
                    <div class="form-group"><label>Username</label><input type="text" name="username" required></div>
                    <button type="submit" class="btn btn-red" style="width:100%;">Send Reset Link</button>
                </form>
            </div>
        </div>
    ''')


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    token = request.args.get('token', '')
    msg = None
    if request.method == 'POST':
        new_password = request.form.get('password', '')
        db = get_db()
        reset = db.execute('SELECT * FROM password_reset_tokens WHERE token = ?', (token,)).fetchone()
        if reset:
            hashed = hashlib.md5(new_password.encode()).hexdigest()
            db.execute('UPDATE users SET password = ? WHERE id = ?', (hashed, reset['user_id']))
            db.commit()
            msg = "Password updated! <a href='/login'>Login now</a>"
        else:
            msg = "Invalid or expired token"

    return render_page("Reset Password", f'''
        <div style="max-width:400px; margin:0 auto;">
            <div class="page-hdr" style="text-align:center;"><h1>New Password</h1></div>
            {'<div class="alert alert-ok">' + msg + '</div>' if msg else ''}
            <div class="card">
                <form method="POST">
                    <div class="form-group"><label>New Password</label><input type="password" name="password" required></div>
                    <button type="submit" class="btn btn-red" style="width:100%;">Update Password</button>
                </form>
            </div>
        </div>
    ''')


@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect('/login')
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    unread = db.execute('SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0', (session['user_id'],)).fetchone()[0]

    if session.get('role') in ('admin', 'recruiter'):
        apps = db.execute('''SELECT a.*, j.title as job_title, u.username as applicant_name
            FROM applications a JOIN jobs j ON a.job_id = j.id JOIN users u ON a.user_id = u.id
            ORDER BY a.created_at DESC''').fetchall()
    else:
        apps = db.execute('''SELECT a.*, j.title as job_title, j.company
            FROM applications a JOIN jobs j ON a.job_id = j.id WHERE a.user_id = ?
            ORDER BY a.created_at DESC''', (session['user_id'],)).fetchall()

    rows = ''
    for a in apps:
        sc = f"s-{a['status']}"
        if session.get('role') in ('admin', 'recruiter'):
            rows += f'<tr><td>{a["job_title"]}</td><td>{a["applicant_name"]}</td><td><span class="status {sc}">{a["status"]}</span></td><td><a href="/application/{a["id"]}" class="btn btn-ghost btn-sm">View</a></td></tr>'
        else:
            rows += f'<tr><td>{a["job_title"]}</td><td>{a["company"]}</td><td><span class="status {sc}">{a["status"]}</span></td><td><a href="/application/{a["id"]}" class="btn btn-ghost btn-sm">View</a></td></tr>'

    if not rows:
        rows = '<tr><td colspan="4" class="empty">No applications yet</td></tr>'

    col2 = "Applicant" if session.get('role') in ('admin', 'recruiter') else "Company"

    return render_page("Dashboard", f'''
        <div class="page-hdr">
            <h1>Dashboard</h1>
            <p>Welcome back, {user["username"]} {'· <a href="/messages" style="color:var(--ylw);">' + str(unread) + ' unread messages</a>' if unread > 0 else ''}</p>
        </div>
        <div class="card">
            <h3>Applications</h3><br>
            <table><tr><th>Position</th><th>{col2}</th><th>Status</th><th></th></tr>{rows}</table>
        </div>
    ''')


@app.route('/profile/<int:user_id>')
def profile(user_id):
    if not session.get('user_id'):
        return redirect('/login')
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return "User not found", 404

    return render_page(f"{user['username']}'s Profile", f'''
        <div class="page-hdr"><h1>{user["username"]}</h1><p><span class="badge">{user["role"]}</span></p></div>
        <div class="grid-2">
            <div class="card">
                <h3>Personal Info</h3><br>
                <table>
                    <tr><td style="color:var(--t3);width:120px;">User ID</td><td>{user["id"]}</td></tr>
                    <tr><td style="color:var(--t3);">Username</td><td>{user["username"]}</td></tr>
                    <tr><td style="color:var(--t3);">Email</td><td>{user["email"]}</td></tr>
                    <tr><td style="color:var(--t3);">Phone</td><td>{user["phone"]}</td></tr>
                    <tr><td style="color:var(--t3);">Address</td><td>{user["address"]}</td></tr>
                    <tr><td style="color:var(--t3);">SSN</td><td>{user["ssn"]}</td></tr>
                </table>
            </div>
            <div class="card">
                <h3>Account</h3><br>
                <table>
                    <tr><td style="color:var(--t3);width:120px;">Role</td><td>{user["role"]}</td></tr>
                    <tr><td style="color:var(--t3);">Bio</td><td>{user["bio"]}</td></tr>
                    <tr><td style="color:var(--t3);">Joined</td><td>{user["created_at"]}</td></tr>
                    <tr><td style="color:var(--t3);">Password Hash</td><td style="font-size:11px;color:var(--t3);word-break:break-all;">{user["password"]}</td></tr>
                </table>
            </div>
        </div>
    ''')


@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if not session.get('user_id'):
        return redirect('/login')
    db = get_db()
    msg = None

    if request.method == 'POST':
        bio = request.form.get('bio', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        role = request.form.get('role', session.get('role'))
        db.execute('UPDATE users SET bio = ?, email = ?, phone = ?, role = ? WHERE id = ?',
                   (bio, email, phone, role, session['user_id']))
        db.commit()
        session['role'] = role
        session['email'] = email
        msg = "Profile updated!"

    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    return render_page("Edit Profile", f'''
        <div style="max-width:500px;margin:0 auto;">
            <div class="page-hdr"><h1>Edit Profile</h1></div>
            {'<div class="alert alert-ok">' + msg + '</div>' if msg else ''}
            <div class="card">
                <form method="POST">
                    <div class="form-group"><label>Email</label><input type="email" name="email" value="{user['email'] or ''}"></div>
                    <div class="form-group"><label>Phone</label><input type="text" name="phone" value="{user['phone'] or ''}"></div>
                    <div class="form-group"><label>Bio</label><textarea name="bio">{user['bio'] or ''}</textarea></div>
                    <input type="hidden" name="role" value="{user['role']}">
                    <button type="submit" class="btn btn-red" style="width:100%;">Save Changes</button>
                </form>
            </div>
        </div>
    ''')


@app.route('/jobs')
def jobs():
    db = get_db()
    all_jobs = db.execute('SELECT * FROM jobs WHERE is_active = 1 ORDER BY created_at DESC').fetchall()
    cards = ''
    for j in all_jobs:
        cards += f'''
        <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:start;">
                <div>
                    <h3>{j["title"]}</h3>
                    <div class="meta">
                        <span>{j["company"]}</span><span>{j["location"]}</span>
                        <span class="salary">{j["salary"]}</span>
                        <span class="job-type">{j["job_type"]}</span>
                    </div>
                    <p>{j["description"]}</p>
                </div>
                <a href="/jobs/{j["id"]}" class="btn btn-red btn-sm" style="white-space:nowrap;">Apply →</a>
            </div>
        </div>'''
    return render_page("Jobs", f'''
        <div class="page-hdr"><h1>Open Positions</h1><p>{len(all_jobs)} opportunities available</p></div>
        {cards}
    ''')


@app.route('/jobs/<int:job_id>', methods=['GET', 'POST'])
def job_detail(job_id):
    if not session.get('user_id'):
        return redirect('/login')
    db = get_db()
    job = db.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    if not job:
        return "Job not found", 404

    msg = None
    if request.method == 'POST':
        cover_letter = request.form.get('cover_letter', '')
        resume = request.files.get('resume')
        resume_path = None
        if resume and resume.filename:
            resume_path = os.path.join(app.config['UPLOAD_FOLDER'], resume.filename)
            resume.save(resume_path)
        db.execute('INSERT INTO applications (job_id, user_id, cover_letter, resume_path, status) VALUES (?,?,?,?,?)',
                   (job_id, session['user_id'], cover_letter, resume_path, 'pending'))
        db.commit()
        msg = "Application submitted successfully!"

    return render_page(job["title"], f'''
        <a href="/jobs" class="btn btn-ghost btn-sm" style="margin-bottom:1.5rem;">← All Jobs</a>
        {'<div class="alert alert-ok">' + msg + '</div>' if msg else ''}
        <div class="page-hdr">
            <h1>{job["title"]}</h1>
            <p>{job["company"]} · {job["location"]} · <span class="job-type">{job["job_type"]}</span></p>
        </div>
        <div class="grid-2">
            <div>
                <div class="card"><h3>Description</h3><br><p>{job["description"]}</p></div>
                <div class="card"><h3>Requirements</h3><br><p>{job["requirements"]}</p></div>
                <div class="card"><p class="salary" style="font-size:1.1rem;">{job["salary"]}</p></div>
            </div>
            <div class="card">
                <h3>Apply Now</h3><br>
                <form method="POST" enctype="multipart/form-data">
                    <div class="form-group"><label>Cover Letter</label><textarea name="cover_letter" placeholder="Tell us why you're a great fit..."></textarea></div>
                    <div class="form-group"><label>Upload Resume</label><input type="file" name="resume"></div>
                    <button type="submit" class="btn btn-red" style="width:100%;">Submit Application</button>
                </form>
            </div>
        </div>
    ''')


@app.route('/application/<int:app_id>', methods=['GET', 'POST'])
def application_detail(app_id):
    if not session.get('user_id'):
        return redirect('/login')
    db = get_db()
    app_data = db.execute('''
        SELECT a.*, j.title as job_title, j.company, u.username, u.email, u.phone, u.ssn, u.address, u.bio
        FROM applications a JOIN jobs j ON a.job_id = j.id JOIN users u ON a.user_id = u.id WHERE a.id = ?
    ''', (app_id,)).fetchone()
    if not app_data:
        return "Application not found", 404

    if request.method == 'POST':
        if 'note' in request.form:
            db.execute('INSERT INTO notes (application_id, author_id, content) VALUES (?,?,?)',
                       (app_id, session['user_id'], request.form.get('note', '')))
            db.commit()
        elif 'status' in request.form:
            db.execute('UPDATE applications SET status = ? WHERE id = ?', (request.form.get('status'), app_id))
            db.commit()
            return redirect(f'/application/{app_id}')

    notes = db.execute('SELECT n.*, u.username FROM notes n JOIN users u ON n.author_id = u.id WHERE n.application_id = ? ORDER BY n.created_at DESC', (app_id,)).fetchall()
    notes_html = ''
    for n in notes:
        notes_html += f'<div class="comment"><div class="author">{n["username"]}</div><div class="text">{n["content"]}</div></div>'

    sc = f"s-{app_data['status']}"
    resume_link = f'<a href="/uploads/{os.path.basename(app_data["resume_path"])}" class="btn btn-ghost btn-sm">Download Resume</a>' if app_data["resume_path"] else '<span style="color:var(--t3);">No resume uploaded</span>'

    status_form = ''
    if session.get('role') in ('admin', 'recruiter'):
        status_form = f'''
        <form method="POST" style="margin-top:1rem;">
            <div style="display:flex;gap:8px;">
                <select name="status" style="flex:1;">
                    <option value="pending">Pending</option><option value="reviewed">Reviewed</option>
                    <option value="interviewed">Interviewed</option><option value="accepted">Accepted</option>
                    <option value="rejected">Rejected</option>
                </select>
                <button type="submit" class="btn btn-ghost btn-sm">Update</button>
            </div>
        </form>'''

    return render_page(f"Application #{app_id}", f'''
        <a href="/dashboard" class="btn btn-ghost btn-sm" style="margin-bottom:1.5rem;">← Dashboard</a>
        <div class="page-hdr"><h1>Application #{app_id}</h1><p>{app_data["job_title"]} at {app_data["company"]}</p></div>
        <div class="grid-2">
            <div>
                <div class="card">
                    <h3>Applicant</h3><br>
                    <table>
                        <tr><td style="color:var(--t3);width:100px;">Name</td><td>{app_data["username"]}</td></tr>
                        <tr><td style="color:var(--t3);">Email</td><td>{app_data["email"]}</td></tr>
                        <tr><td style="color:var(--t3);">Phone</td><td>{app_data["phone"]}</td></tr>
                        <tr><td style="color:var(--t3);">Address</td><td>{app_data["address"]}</td></tr>
                        <tr><td style="color:var(--t3);">SSN</td><td>{app_data["ssn"]}</td></tr>
                        <tr><td style="color:var(--t3);">Bio</td><td>{app_data["bio"]}</td></tr>
                    </table>
                </div>
                <div class="card"><h3>Cover Letter</h3><br><p>{app_data["cover_letter"]}</p></div>
            </div>
            <div>
                <div class="card">
                    <h3>Status: <span class="status {sc}">{app_data['status']}</span></h3>
                    <br>{resume_link}
                    {status_form}
                </div>
                <div class="card">
                    <h3>Notes</h3><br>
                    <form method="POST"><div class="form-group"><textarea name="note" placeholder="Add a note..." rows="3"></textarea></div><button type="submit" class="btn btn-red btn-sm">Add Note</button></form>
                    {notes_html if notes_html else '<p style="color:var(--t3);font-size:13px;margin-top:1rem;">No notes yet</p>'}
                </div>
            </div>
        </div>
    ''')


@app.route('/messages')
def messages_inbox():
    if not session.get('user_id'):
        return redirect('/login')
    db = get_db()
    msgs = db.execute('''
        SELECT m.*, u.username as sender_name FROM messages m
        JOIN users u ON m.sender_id = u.id WHERE m.receiver_id = ? ORDER BY m.created_at DESC
    ''', (session['user_id'],)).fetchall()

    rows = ''
    for m in msgs:
        unread = 'msg-unread' if not m['is_read'] else ''
        rows += f'''
        <a href="/messages/{m['id']}" style="text-decoration:none;color:inherit;">
            <div class="msg-row">
                <div><div class="msg-subject {unread}">{m['subject']}</div><div class="msg-from">From: {m['sender_name']}</div></div>
                <div class="msg-date">{m['created_at']}</div>
            </div>
        </a>'''
    if not rows:
        rows = '<div class="empty"><p>No messages</p></div>'

    return render_page("Messages", f'''
        <div class="page-hdr">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div><h1>Messages</h1><p>Your inbox</p></div>
                <a href="/messages/compose" class="btn btn-red btn-sm">New Message</a>
            </div>
        </div>
        <div class="card">{rows}</div>
    ''')


@app.route('/messages/<int:msg_id>')
def view_message(msg_id):
    if not session.get('user_id'):
        return redirect('/login')
    db = get_db()
    msg = db.execute('''SELECT m.*, u.username as sender_name FROM messages m
        JOIN users u ON m.sender_id = u.id WHERE m.id = ?''', (msg_id,)).fetchone()
    if not msg:
        return "Message not found", 404
    db.execute('UPDATE messages SET is_read = 1 WHERE id = ?', (msg_id,))
    db.commit()

    return render_page("Message", f'''
        <a href="/messages" class="btn btn-ghost btn-sm" style="margin-bottom:1.5rem;">← Inbox</a>
        <div class="card">
            <h3>{msg['subject']}</h3>
            <div class="meta"><span>From: {msg['sender_name']}</span><span>{msg['created_at']}</span></div>
            <p style="margin-top:1rem;">{msg['body']}</p>
        </div>
    ''')


@app.route('/messages/compose', methods=['GET', 'POST'])
def compose_message():
    if not session.get('user_id'):
        return redirect('/login')
    msg = None
    if request.method == 'POST':
        to_user = request.form.get('to', '')
        subject = request.form.get('subject', '')
        body = request.form.get('body', '')
        db = get_db()
        recipient = db.execute(f"SELECT id FROM users WHERE username = '{to_user}'").fetchone()
        if recipient:
            db.execute('INSERT INTO messages (sender_id, receiver_id, subject, body) VALUES (?,?,?,?)',
                       (session['user_id'], recipient['id'], subject, body))
            db.commit()
            msg = "Message sent!"
        else:
            msg = f"User '{to_user}' not found"

    return render_page("Compose", f'''
        <div style="max-width:500px;margin:0 auto;">
            <div class="page-hdr"><h1>New Message</h1></div>
            {'<div class="alert alert-ok">' + msg + '</div>' if msg and 'sent' in msg else ('<div class="alert alert-err">' + msg + '</div>' if msg else '')}
            <div class="card">
                <form method="POST">
                    <div class="form-group"><label>To (username)</label><input type="text" name="to" required></div>
                    <div class="form-group"><label>Subject</label><input type="text" name="subject" required></div>
                    <div class="form-group"><label>Message</label><textarea name="body" required></textarea></div>
                    <button type="submit" class="btn btn-red" style="width:100%;">Send</button>
                </form>
            </div>
        </div>
    ''')


@app.route('/search')
def search():
    if not session.get('user_id'):
        return redirect('/login')
    query = request.args.get('q', '')
    results_html = ''
    if query:
        db = get_db()
        sql = f"SELECT * FROM jobs WHERE title LIKE '%{query}%' OR description LIKE '%{query}%' OR company LIKE '%{query}%'"
        try:
            results = db.execute(sql).fetchall()
            for r in results:
                results_html += f'''<div class="card"><h3>{r["title"]}</h3><div class="meta"><span>{r["company"]}</span><span>{r["location"]}</span></div><a href="/jobs/{r["id"]}" class="btn btn-ghost btn-sm">View</a></div>'''
            if not results:
                results_html = f'<div class="empty"><p>No results for "{query}"</p></div>'
        except Exception as e:
            results_html = f'<div class="alert alert-err">Search error: {str(e)}</div>'

    return render_page("Search", f'''
        <div class="page-hdr"><h1>Search Jobs</h1></div>
        <div class="card">
            <form method="GET"><div style="display:flex;gap:10px;">
                <input type="text" name="q" value="{query}" placeholder="Search by title, company, or keywords...">
                <button type="submit" class="btn btn-red">Search</button>
            </div></form>
        </div>
        {f'<p style="color:var(--t2);margin:1rem 0;font-size:13px;">Results for: <strong>{query}</strong></p>' if query else ''}
        {results_html}
    ''')


@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    result = None
    if request.method == 'POST':
        name = request.form.get('name', '')
        message = request.form.get('message', '')
        thank_you = f"Thank you, {name}! We received your feedback: '{message}'."
        result = render_template_string(thank_you)

    return render_page("Feedback", f'''
        <div style="max-width:500px;margin:0 auto;">
            <div class="page-hdr"><h1>Feedback</h1><p>Help us improve</p></div>
            {'<div class="alert alert-ok">' + str(result) + '</div>' if result else ''}
            <div class="card">
                <form method="POST">
                    <div class="form-group"><label>Your Name</label><input type="text" name="name" required></div>
                    <div class="form-group"><label>Feedback</label><textarea name="message" placeholder="Share your thoughts..."></textarea></div>
                    <button type="submit" class="btn btn-red" style="width:100%;">Submit</button>
                </form>
            </div>
        </div>
    ''')


@app.route('/admin')
def admin_panel():
    if not session.get('user_id'):
        return redirect('/login')
    db = get_db()
    users = db.execute('SELECT * FROM users').fetchall()
    jobs_list = db.execute('SELECT j.*, u.username as posted_by_name FROM jobs j JOIN users u ON j.posted_by = u.id ORDER BY j.created_at DESC').fetchall()

    users_html = ''
    for u in users:
        users_html += f'''<tr><td>{u["id"]}</td><td>{u["username"]}</td><td>{u["email"]}</td><td>{u["phone"]}</td>
            <td style="font-size:12px;">{u["ssn"]}</td><td><span class="badge">{u["role"]}</span></td>
            <td style="font-size:10px;color:var(--t3);word-break:break-all;">{u["password"]}</td></tr>'''

    jobs_html = ''
    for j in jobs_list:
        jobs_html += f'<tr><td>{j["id"]}</td><td>{j["title"]}</td><td>{j["company"]}</td><td>{j["posted_by_name"]}</td><td>{"Active" if j["is_active"] else "Inactive"}</td></tr>'

    return render_page("Admin", f'''
        <div class="page-hdr"><h1>Admin Panel</h1><p>Manage users, jobs, and system settings</p></div>
        <div class="tabs">
            <a href="#users" class="active">Users</a>
            <a href="#jobs">Jobs</a>
            <a href="#tools">Tools</a>
        </div>
        <div class="card" style="overflow-x:auto;">
            <h3>All Users ({len(users)})</h3><br>
            <table><tr><th>ID</th><th>User</th><th>Email</th><th>Phone</th><th>SSN</th><th>Role</th><th>Password Hash</th></tr>{users_html}</table>
        </div>
        <div class="card" style="overflow-x:auto;">
            <h3>All Jobs ({len(jobs_list)})</h3><br>
            <table><tr><th>ID</th><th>Title</th><th>Company</th><th>Posted By</th><th>Status</th></tr>{jobs_html}</table>
        </div>
        <div class="card">
            <h3>Post New Job</h3><br>
            <form method="POST" action="/admin/create-job">
                <div class="grid-2">
                    <div class="form-group"><label>Job Title</label><input type="text" name="title" required></div>
                    <div class="form-group"><label>Company</label><input type="text" name="company" required></div>
                </div>
                <div class="form-group"><label>Description</label><textarea name="description"></textarea></div>
                <div class="form-group"><label>Requirements</label><textarea name="requirements"></textarea></div>
                <div class="grid-2">
                    <div class="form-group"><label>Salary</label><input type="text" name="salary"></div>
                    <div class="form-group"><label>Location</label><input type="text" name="location"></div>
                </div>
                <div class="form-group"><label>Job Type</label><select name="job_type"><option>full-time</option><option>part-time</option><option>contract</option><option>remote</option><option>hybrid</option></select></div>
                <button type="submit" class="btn btn-red">Post Job</button>
            </form>
        </div>
        <div class="card">
            <h3>System Tools</h3><br>
            <form method="POST" action="/admin/export">
                <div class="form-group"><label>Export Data (table name)</label><input type="text" name="table" placeholder="e.g. users, jobs, applications"></div>
                <button type="submit" class="btn btn-ghost">Export CSV</button>
            </form>
            <br>
            <form method="POST" action="/admin/health-check">
                <div class="form-group"><label>Server Health Check (hostname)</label><input type="text" name="host" placeholder="e.g. localhost"></div>
                <button type="submit" class="btn btn-ghost">Run Check</button>
            </form>
        </div>
    ''')


@app.route('/admin/create-job', methods=['POST'])
def create_job():
    if not session.get('user_id'):
        return redirect('/login')
    db = get_db()
    db.execute('INSERT INTO jobs (title, company, description, requirements, salary, location, job_type, posted_by) VALUES (?,?,?,?,?,?,?,?)',
               (request.form.get('title'), request.form.get('company'), request.form.get('description'),
                request.form.get('requirements'), request.form.get('salary'), request.form.get('location'),
                request.form.get('job_type', 'full-time'), session['user_id']))
    db.commit()
    return redirect('/jobs')


@app.route('/admin/export', methods=['POST'])
def admin_export():
    if not session.get('user_id'):
        return redirect('/login')
    table = request.form.get('table', 'jobs')
    db = get_db()
    try:
        rows = db.execute(f'SELECT * FROM {table}').fetchall()
        if rows:
            headers = rows[0].keys()
            csv_data = ','.join(headers) + '\n'
            for r in rows:
                csv_data += ','.join(str(r[h]) for h in headers) + '\n'
            response = make_response(csv_data)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename={table}_export.csv'
            return response
        return "No data found", 404
    except Exception as e:
        return f"Export error: {str(e)}", 500


@app.route('/admin/health-check', methods=['POST'])
def health_check():
    if not session.get('user_id'):
        return redirect('/login')
    host = request.form.get('host', 'localhost')
    try:
        result = subprocess.check_output(f'ping -c 1 {host}', shell=True, timeout=5, stderr=subprocess.STDOUT)
        return render_page("Health Check", f'''
            <div class="page-hdr"><h1>Health Check</h1></div>
            <div class="card"><h3>Result for: {host}</h3><br><pre style="background:var(--bg);padding:1rem;border-radius:6px;font-size:12px;color:var(--t2);overflow-x:auto;">{result.decode()}</pre></div>
            <a href="/admin" class="btn btn-ghost btn-sm">← Back to Admin</a>
        ''')
    except Exception as e:
        return render_page("Health Check", f'''
            <div class="page-hdr"><h1>Health Check</h1></div>
            <div class="alert alert-err">Check failed for {host}: {str(e)}</div>
            <a href="/admin" class="btn btn-ghost btn-sm">← Back to Admin</a>
        ''')


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ── API Endpoints ─────────────────────────────────────────────

@app.route('/api/users')
def api_users():
    db = get_db()
    users = db.execute('SELECT id, username, email, phone, ssn, password, role, address, bio, created_at FROM users').fetchall()
    return jsonify([dict(u) for u in users])

@app.route('/api/users/<int:user_id>')
def api_user_detail(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        return jsonify(dict(user))
    return jsonify({'error': 'not found'}), 404

@app.route('/api/applications')
def api_applications():
    db = get_db()
    apps = db.execute('''SELECT a.*, u.username, u.email, u.ssn, u.phone, j.title as job_title, j.company
        FROM applications a JOIN users u ON a.user_id = u.id JOIN jobs j ON a.job_id = j.id''').fetchall()
    return jsonify([dict(a) for a in apps])

@app.route('/api/jobs')
def api_jobs():
    db = get_db()
    jobs = db.execute('SELECT * FROM jobs').fetchall()
    return jsonify([dict(j) for j in jobs])

@app.route('/api/messages')
def api_messages():
    db = get_db()
    msgs = db.execute('SELECT * FROM messages').fetchall()
    return jsonify([dict(m) for m in msgs])

@app.route('/api/update-role', methods=['POST'])
def update_role():
    if not session.get('user_id'):
        return jsonify({'error': 'Not authenticated'}), 401
    new_role = request.json.get('role', 'applicant') if request.is_json else request.form.get('role', 'applicant')
    db = get_db()
    db.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, session['user_id']))
    db.commit()
    session['role'] = new_role
    return jsonify({'success': True, 'new_role': new_role})

@app.route('/api/delete-user/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    db = get_db()
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()
    return jsonify({'deleted': user_id})


# ── Debug / Status ────────────────────────────────────────────

@app.route('/debug/config')
def debug_config():
    return jsonify({
        'secret_key': app.secret_key,
        'debug': app.config['DEBUG'],
        'database': app.config['DATABASE'],
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'server_name': app.config.get('SERVER_NAME'),
    })

@app.route('/robots.txt')
def robots():
    return "User-agent: *\nDisallow: /admin\nDisallow: /api/\nDisallow: /debug/\nDisallow: /uploads/\n"


# ── Init ──────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
