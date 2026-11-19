"""
Medi-Civic: Student Grievance Reporting & Priority-Management System
Flask Backend Application
"""

import os
import sqlite3
import hashlib
import secrets
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, g
)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'medi_civic.db')


# ─── Database Helpers ───────────────────────────────────────────────────────────

def get_db():
    """Get a database connection for the current request."""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database with schema and seed data."""
    db = sqlite3.connect(app.config['DATABASE'])
    db.execute("PRAGMA foreign_keys = ON")

    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            department TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            icon TEXT DEFAULT '📋'
        );

        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            urgency INTEGER NOT NULL DEFAULT 3,
            importance INTEGER NOT NULL DEFAULT 3,
            priority_score REAL NOT NULL DEFAULT 5.0,
            priority_level TEXT NOT NULL DEFAULT 'Medium',
            status TEXT NOT NULL DEFAULT 'Submitted',
            assigned_to INTEGER,
            resolution_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (student_id) REFERENCES users(id),
            FOREIGN KEY (assigned_to) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS complaint_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER NOT NULL,
            updated_by INTEGER NOT NULL,
            old_status TEXT,
            new_status TEXT,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id),
            FOREIGN KEY (updated_by) REFERENCES users(id)
        );
    """)

    # Seed categories
    categories = [
        ('Infrastructure', 'Building, classroom, lab equipment issues', '🏗️'),
        ('Sanitation', 'Cleanliness, washroom, water supply issues', '🧹'),
        ('Academic', 'Course, exam, faculty, syllabus-related issues', '📚'),
        ('Safety', 'Security, fire safety, electrical hazards', '🛡️'),
        ('Hostel', 'Room, mess, curfew, maintenance issues', '🏠'),
        ('Transportation', 'Bus routes, timing, vehicle condition issues', '🚌'),
        ('Administrative', 'Fee, certificate, office-related issues', '📄'),
        ('IT & Network', 'WiFi, lab computers, software issues', '💻'),
        ('Other', 'Issues not covered by other categories', '📌'),
    ]
    for name, desc, icon in categories:
        db.execute(
            "INSERT OR IGNORE INTO categories (name, description, icon) VALUES (?, ?, ?)",
            (name, desc, icon)
        )

    # Seed admin + sample student accounts
    def hash_pw(pw):
        return hashlib.sha256(pw.encode()).hexdigest()

    # Admin
    db.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, full_name, email, role, department) VALUES (?, ?, ?, ?, ?, ?)",
        ('admin', hash_pw('admin123'), 'Dr. Admin Authority', 'admin@medicivic.edu', 'admin', 'Administration')
    )
    # Authority
    db.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, full_name, email, role, department) VALUES (?, ?, ?, ?, ?, ?)",
        ('authority', hash_pw('auth123'), 'Prof. Dean of Students', 'dean@medicivic.edu', 'authority', 'Student Affairs')
    )
    # Sample student
    db.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, full_name, email, role, department) VALUES (?, ?, ?, ?, ?, ?)",
        ('student1', hash_pw('student123'), 'Rahul Sharma', 'rahul@medicivic.edu', 'student', 'Computer Science')
    )

    db.commit()
    db.close()


# ─── Priority Calculation ────────────────────────────────────────────────────────

def calculate_priority(urgency, importance):
    """
    Calculate priority score and level based on urgency and importance.
    Uses a weighted formula: priority = 0.6 * urgency + 0.4 * importance
    Scale: 1 (lowest) to 5 (highest) for both dimensions.
    """
    score = round(0.6 * urgency + 0.4 * importance, 2)
    if score >= 4.0:
        level = 'Critical'
    elif score >= 3.0:
        level = 'High'
    elif score >= 2.0:
        level = 'Medium'
    else:
        level = 'Low'
    return score, level


# ─── Auth Helpers ────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def authority_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') not in ('admin', 'authority'):
            flash('Access denied. Authority privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


# ─── Routes ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if user and user['password_hash'] == hashlib.sha256(password.encode()).hexdigest():
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            flash(f'Welcome, {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        department = request.form.get('department', '').strip()

        if not all([username, password, full_name, email]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            flash('Username already exists.', 'danger')
            return render_template('register.html')

        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        db.execute(
            "INSERT INTO users (username, password_hash, full_name, email, role, department) VALUES (?, ?, ?, ?, 'student', ?)",
            (username, pw_hash, full_name, email, department)
        )
        db.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    role = session.get('role')

    if role == 'student':
        complaints = db.execute("""
            SELECT c.*, cat.name as category_name, cat.icon as category_icon
            FROM complaints c
            JOIN categories cat ON c.category_id = cat.id
            WHERE c.student_id = ?
            ORDER BY c.created_at DESC
        """, (session['user_id'],)).fetchall()

        stats = {
            'total': len(complaints),
            'pending': sum(1 for c in complaints if c['status'] in ('Submitted', 'Under Review')),
            'in_progress': sum(1 for c in complaints if c['status'] == 'In Progress'),
            'resolved': sum(1 for c in complaints if c['status'] == 'Resolved'),
        }
    else:
        complaints = db.execute("""
            SELECT c.*, cat.name as category_name, cat.icon as category_icon,
                   u.full_name as student_name, u.department as student_dept
            FROM complaints c
            JOIN categories cat ON c.category_id = cat.id
            JOIN users u ON c.student_id = u.id
            ORDER BY c.priority_score DESC, c.created_at ASC
        """).fetchall()

        stats = {
            'total': len(complaints),
            'critical': sum(1 for c in complaints if c['priority_level'] == 'Critical'),
            'high': sum(1 for c in complaints if c['priority_level'] == 'High'),
            'pending': sum(1 for c in complaints if c['status'] in ('Submitted', 'Under Review')),
            'resolved': sum(1 for c in complaints if c['status'] == 'Resolved'),
        }

    return render_template('dashboard.html', complaints=complaints, stats=stats)


@app.route('/complaint/new', methods=['GET', 'POST'])
@login_required
def new_complaint():
    db = get_db()
    categories = db.execute("SELECT * FROM categories ORDER BY name").fetchall()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category_id = request.form.get('category_id', type=int)
        urgency = request.form.get('urgency', 3, type=int)
        importance = request.form.get('importance', 3, type=int)

        if not all([title, description, category_id]):
            flash('Title, description and category are required.', 'danger')
            return render_template('new_complaint.html', categories=categories)

        urgency = max(1, min(5, urgency))
        importance = max(1, min(5, importance))
        score, level = calculate_priority(urgency, importance)

        db.execute("""
            INSERT INTO complaints (title, description, category_id, student_id,
                                    urgency, importance, priority_score, priority_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, description, category_id, session['user_id'],
              urgency, importance, score, level))
        db.commit()
        flash('Complaint submitted successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('new_complaint.html', categories=categories)


@app.route('/complaint/<int:complaint_id>')
@login_required
def view_complaint(complaint_id):
    db = get_db()
    complaint = db.execute("""
        SELECT c.*, cat.name as category_name, cat.icon as category_icon,
               u.full_name as student_name, u.email as student_email, u.department as student_dept
        FROM complaints c
        JOIN categories cat ON c.category_id = cat.id
        JOIN users u ON c.student_id = u.id
        WHERE c.id = ?
    """, (complaint_id,)).fetchone()

    if not complaint:
        flash('Complaint not found.', 'danger')
        return redirect(url_for('dashboard'))

    # Students can only view their own complaints
    if session['role'] == 'student' and complaint['student_id'] != session['user_id']:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    updates = db.execute("""
        SELECT cu.*, u.full_name as updater_name, u.role as updater_role
        FROM complaint_updates cu
        JOIN users u ON cu.updated_by = u.id
        WHERE cu.complaint_id = ?
        ORDER BY cu.created_at DESC
    """, (complaint_id,)).fetchall()

    return render_template('view_complaint.html', complaint=complaint, updates=updates)


@app.route('/complaint/<int:complaint_id>/update', methods=['POST'])
@authority_required
def update_complaint(complaint_id):
    db = get_db()
    complaint = db.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if not complaint:
        flash('Complaint not found.', 'danger')
        return redirect(url_for('dashboard'))

    new_status = request.form.get('status', '').strip()
    comment = request.form.get('comment', '').strip()
    resolution_notes = request.form.get('resolution_notes', '').strip()

    valid_statuses = ['Submitted', 'Under Review', 'In Progress', 'Escalated', 'Resolved', 'Closed']
    if new_status not in valid_statuses:
        flash('Invalid status.', 'danger')
        return redirect(url_for('view_complaint', complaint_id=complaint_id))

    old_status = complaint['status']
    resolved_at = datetime.now().isoformat() if new_status in ('Resolved', 'Closed') else None

    db.execute("""
        UPDATE complaints
        SET status = ?, resolution_notes = COALESCE(?, resolution_notes),
            updated_at = CURRENT_TIMESTAMP, resolved_at = COALESCE(?, resolved_at)
        WHERE id = ?
    """, (new_status, resolution_notes or None, resolved_at, complaint_id))

    db.execute("""
        INSERT INTO complaint_updates (complaint_id, updated_by, old_status, new_status, comment)
        VALUES (?, ?, ?, ?, ?)
    """, (complaint_id, session['user_id'], old_status, new_status, comment))

    db.commit()
    flash(f'Complaint status updated to "{new_status}".', 'success')
    return redirect(url_for('view_complaint', complaint_id=complaint_id))


@app.route('/analytics')
@authority_required
def analytics():
    db = get_db()

    # Category distribution
    category_stats = db.execute("""
        SELECT cat.name, cat.icon, COUNT(c.id) as count
        FROM categories cat
        LEFT JOIN complaints c ON c.category_id = cat.id
        GROUP BY cat.id
        ORDER BY count DESC
    """).fetchall()

    # Priority distribution
    priority_stats = db.execute("""
        SELECT priority_level, COUNT(*) as count
        FROM complaints
        GROUP BY priority_level
    """).fetchall()

    # Status distribution
    status_stats = db.execute("""
        SELECT status, COUNT(*) as count
        FROM complaints
        GROUP BY status
    """).fetchall()

    # Recent complaints
    recent = db.execute("""
        SELECT c.*, cat.name as category_name, u.full_name as student_name
        FROM complaints c
        JOIN categories cat ON c.category_id = cat.id
        JOIN users u ON c.student_id = u.id
        ORDER BY c.priority_score DESC
        LIMIT 10
    """).fetchall()

    total = db.execute("SELECT COUNT(*) as n FROM complaints").fetchone()['n']

    return render_template('analytics.html',
                           category_stats=category_stats,
                           priority_stats=priority_stats,
                           status_stats=status_stats,
                           recent=recent,
                           total=total)


# ─── API Endpoints (for AJAX) ───────────────────────────────────────────────────

@app.route('/api/priority-preview', methods=['POST'])
@login_required
def priority_preview():
    data = request.get_json()
    urgency = max(1, min(5, int(data.get('urgency', 3))))
    importance = max(1, min(5, int(data.get('importance', 3))))
    score, level = calculate_priority(urgency, importance)
    return jsonify({'score': score, 'level': level})


# ─── Entry Point ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    print("\n✅ Medi-Civic is running!")
    print("📌 Open http://127.0.0.1:5000 in your browser")
    print("\n🔐 Demo Accounts:")
    print("   Student:   student1 / student123")
    print("   Authority: authority / auth123")
    print("   Admin:     admin / admin123\n")
    app.run(debug=True, port=5000)
