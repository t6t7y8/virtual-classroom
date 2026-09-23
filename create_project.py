import os

# ============================================================
# VIRTUAL CLASSROOM PROJECT GENERATOR
# Creates the complete project structure inside the
# already-existing virtual-classroom folder.
# ============================================================

# Get the folder where this script is located
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


# ============================================================
# PROJECT FILES
# ============================================================

files = {
    ".env": """SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///virtual_classroom.db
""",

    "requirements.txt": """Flask
Flask-SQLAlchemy
Flask-Login
python-dotenv
Werkzeug
""",

    "app.py": '''import os

from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "development-secret-key"
)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///virtual_classroom.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# ============================================================
# EXTENSIONS
# ============================================================

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."


# ============================================================
# DATABASE MODELS
# ============================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        default="student"
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classroom.id"),
        nullable=False
    )

    due_date = db.Column(
        db.DateTime,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


# ============================================================
# LOGIN MANAGER
# ============================================================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")

        if not name or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            flash("An account with this email already exists.", "danger")
            return redirect(url_for("register"))

        if role not in ["student", "teacher"]:
            role = "student"

        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role=role
        )

        db.session.add(user)
        db.session.commit()

        flash(
            "Registration successful. You can now log in.",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("register.html")


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(
            email=email
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):
            login_user(user)

            flash(
                "Welcome back!",
                "success"
            )

            next_page = request.args.get("next")

            if next_page:
                return redirect(next_page)

            return redirect(url_for("dashboard"))

        flash(
            "Invalid email or password.",
            "danger"
        )

    return render_template("login.html")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(url_for("index"))


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():

    classrooms = Classroom.query.all()
    assignments = Assignment.query.all()

    return render_template(
        "dashboard.html",
        classrooms=classrooms,
        assignments=assignments
    )


# ============================================================
# CLASSROOM
# ============================================================

@app.route("/classroom/<int:classroom_id>")
@login_required
def classroom(classroom_id):

    classroom_data = db.session.get(
        Classroom,
        classroom_id
    )

    if not classroom_data:
        flash(
            "Classroom not found.",
            "danger"
        )

        return redirect(url_for("dashboard"))

    assignments = Assignment.query.filter_by(
        classroom_id=classroom_id
    ).all()

    return render_template(
        "classroom.html",
        classroom=classroom_data,
        assignments=assignments
    )


# ============================================================
# ASSIGNMENT
# ============================================================

@app.route("/assignment/<int:assignment_id>")
@login_required
def assignment(assignment_id):

    assignment_data = db.session.get(
        Assignment,
        assignment_id
    )

    if not assignment_data:
        flash(
            "Assignment not found.",
            "danger"
        )

        return redirect(url_for("dashboard"))

    classroom_data = db.session.get(
        Classroom,
        assignment_data.classroom_id
    )

    return render_template(
        "assignment.html",
        assignment=assignment_data,
        classroom=classroom_data
    )


# ============================================================
# CREATE DATABASE
# ============================================================

with app.app_context():
    db.create_all()


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
''',

    # ========================================================
    # TEMPLATES
    # ========================================================

    "templates/base.html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>
        {% block title %}Virtual Classroom{% endblock %}
    </title>

    <link
        rel="stylesheet"
        href="{{ url_for('static', filename='css/style.css') }}"
    >
</head>

<body>

<nav class="navbar">

    <div class="container nav-container">

        <a
            href="{{ url_for('index') }}"
            class="logo"
        >
            Virtual Classroom
        </a>

        <div class="nav-links">

            <a href="{{ url_for('index') }}">
                Home
            </a>

            {% if current_user.is_authenticated %}

                <a href="{{ url_for('dashboard') }}">
                    Dashboard
                </a>

                <a href="{{ url_for('logout') }}">
                    Logout
                </a>

            {% else %}

                <a href="{{ url_for('login') }}">
                    Login
                </a>

                <a href="{{ url_for('register') }}">
                    Register
                </a>

            {% endif %}

        </div>

    </div>

</nav>


<main class="container">

    {% with messages = get_flashed_messages(with_categories=true) %}

        {% if messages %}

            {% for category, message in messages %}

                <div class="alert {{ category }}">
                    {{ message }}
                </div>

            {% endfor %}

        {% endif %}

    {% endwith %}


    {% block content %}{% endblock %}

</main>


<footer>

    <p>
        &copy; 2026 Virtual Classroom. All rights reserved.
    </p>

</footer>

</body>
</html>
''',

    "templates/index.html": '''{% extends "base.html" %}

{% block title %}
Virtual Classroom - Home
{% endblock %}

{% block content %}

<section class="hero">

    <div class="hero-content">

        <h1>
            Welcome to Virtual Classroom
        </h1>

        <p>
            Learn, teach, collaborate and manage
            your classes from one convenient platform.
        </p>

        {% if current_user.is_authenticated %}

            <a
                href="{{ url_for('dashboard') }}"
                class="btn"
            >
                Go to Dashboard
            </a>

        {% else %}

            <div class="hero-buttons">

                <a
                    href="{{ url_for('register') }}"
                    class="btn"
                >
                    Get Started
                </a>

                <a
                    href="{{ url_for('login') }}"
                    class="btn btn-secondary"
                >
                    Login
                </a>

            </div>

        {% endif %}

    </div>

</section>


<section class="features">

    <div class="feature-card">

        <h3>
            Virtual Classes
        </h3>

        <p>
            Access your classrooms and learning
            materials from anywhere.
        </p>

    </div>


    <div class="feature-card">

        <h3>
            Assignments
        </h3>

        <p>
            View assignments and keep track
            of your academic activities.
        </p>

    </div>


    <div class="feature-card">

        <h3>
            Collaboration
        </h3>

        <p>
            Connect teachers and students
            through a simple classroom system.
        </p>

    </div>

</section>

{% endblock %}
''',

    "templates/login.html": '''{% extends "base.html" %}

{% block title %}
Login - Virtual Classroom
{% endblock %}

{% block content %}

<div class="auth-container">

    <div class="auth-card">

        <h2>
            Login
        </h2>

        <p>
            Sign in to access your classroom.
        </p>

        <form method="POST">

            <div class="form-group">

                <label for="email">
                    Email
                </label>

                <input
                    type="email"
                    id="email"
                    name="email"
                    placeholder="Enter your email"
                    required
                >

            </div>


            <div class="form-group">

                <label for="password">
                    Password
                </label>

                <input
                    type="password"
                    id="password"
                    name="password"
                    placeholder="Enter your password"
                    required
                >

            </div>


            <button
                type="submit"
                class="btn full-width"
            >
                Login
            </button>

        </form>


        <p class="auth-footer">

            Don't have an account?

            <a href="{{ url_for('register') }}">
                Register
            </a>

        </p>

    </div>

</div>

{% endblock %}
''',

    "templates/register.html": '''{% extends "base.html" %}

{% block title %}
Register - Virtual Classroom
{% endblock %}

{% block content %}

<div class="auth-container">

    <div class="auth-card">

        <h2>
            Create Account
        </h2>

        <p>
            Join the virtual classroom.
        </p>

        <form method="POST">

            <div class="form-group">

                <label for="name">
                    Full Name
                </label>

                <input
                    type="text"
                    id="name"
                    name="name"
                    placeholder="Enter your full name"
                    required
                >

            </div>


            <div class="form-group">

                <label for="email">
                    Email
                </label>

                <input
                    type="email"
                    id="email"
                    name="email"
                    placeholder="Enter your email"
                    required
                >

            </div>


            <div class="form-group">

                <label for="password">
                    Password
                </label>

                <input
                    type="password"
                    id="password"
                    name="password"
                    placeholder="Create a password"
                    required
                >

            </div>


            <div class="form-group">

                <label for="role">
                    Account Type
                </label>

                <select
                    id="role"
                    name="role"
                >

                    <option value="student">
                        Student
                    </option>

                    <option value="teacher">
                        Teacher
                    </option>

                </select>

            </div>


            <button
                type="submit"
                class="btn full-width"
            >
                Register
            </button>

        </form>


        <p class="auth-footer">

            Already have an account?

            <a href="{{ url_for('login') }}">
                Login
            </a>

        </p>

    </div>

</div>

{% endblock %}
''',

    "templates/dashboard.html": '''{% extends "base.html" %}

{% block title %}
Dashboard - Virtual Classroom
{% endblock %}

{% block content %}

<div class="dashboard-header">

    <div>

        <h1>
            Dashboard
        </h1>

        <p>
            Welcome, {{ current_user.name }}.
        </p>

    </div>

</div>


<section class="dashboard-section">

    <h2>
        Your Classrooms
    </h2>

    {% if classrooms %}

        <div class="card-grid">

            {% for classroom in classrooms %}

                <div class="classroom-card">

                    <h3>
                        {{ classroom.name }}
                    </h3>

                    <p>
                        {{ classroom.description or
                        "No description available." }}
                    </p>

                    <a
                        href="{{ url_for(
                            'classroom',
                            classroom_id=classroom.id
                        ) }}"
                        class="btn"
                    >
                        Enter Classroom
                    </a>

                </div>

            {% endfor %}

        </div>

    {% else %}

        <div class="empty-state">

            <p>
                No classrooms are available yet.
            </p>

        </div>

    {% endif %}

</section>


<section class="dashboard-section">

    <h2>
        Assignments
    </h2>

    {% if assignments %}

        <div class="assignment-list">

            {% for assignment in assignments %}

                <div class="assignment-card">

                    <div>

                        <h3>
                            {{ assignment.title }}
                        </h3>

                        <p>
                            {{ assignment.description or
                            "No description available." }}
                        </p>

                    </div>

                    <a
                        href="{{ url_for(
                            'assignment',
                            assignment_id=assignment.id
                        ) }}"
                        class="btn"
                    >
                        View
                    </a>

                </div>

            {% endfor %}

        </div>

    {% else %}

        <div class="empty-state">

            <p>
                No assignments available.
            </p>

        </div>

    {% endif %}

</section>

{% endblock %}
''',

    "templates/classroom.html": '''{% extends "base.html" %}

{% block title %}
{{ classroom.name }} - Virtual Classroom
{% endblock %}

{% block content %}

<div class="classroom-header">

    <h1>
        {{ classroom.name }}
    </h1>

    <p>
        {{ classroom.description or
        "Welcome to this classroom." }}
    </p>

</div>


<section class="dashboard-section">

    <h2>
        Classroom Assignments
    </h2>

    {% if assignments %}

        <div class="assignment-list">

            {% for assignment in assignments %}

                <div class="assignment-card">

                    <div>

                        <h3>
                            {{ assignment.title }}
                        </h3>

                        <p>
                            {{ assignment.description or
                            "No description available." }}
                        </p>

                        {% if assignment.due_date %}

                            <small>
                                Due:
                                {{ assignment.due_date }}
                            </small>

                        {% endif %}

                    </div>

                    <a
                        href="{{ url_for(
                            'assignment',
                            assignment_id=assignment.id
                        ) }}"
                        class="btn"
                    >
                        View Assignment
                    </a>

                </div>

            {% endfor %}

        </div>

    {% else %}

        <div class="empty-state">

            <p>
                No assignments have been posted
                for this classroom.
            </p>

        </div>

    {% endif %}

</section>


<a
    href="{{ url_for('dashboard') }}"
    class="back-link"
>
    &larr; Back to Dashboard
</a>

{% endblock %}
''',

    "templates/assignment.html": '''{% extends "base.html" %}

{% block title %}
{{ assignment.title }} - Virtual Classroom
{% endblock %}

{% block content %}

<div class="assignment-detail">

    <div class="assignment-header">

        <span class="badge">
            Assignment
        </span>

        <h1>
            {{ assignment.title }}
        </h1>

        {% if classroom %}

            <p>
                Classroom:
                <strong>
                    {{ classroom.name }}
                </strong>
            </p>

        {% endif %}

    </div>


    <div class="assignment-content">

        <h2>
            Description
        </h2>

        <p>
            {{ assignment.description or
            "No description was provided." }}
        </p>


        {% if assignment.due_date %}

            <div class="due-date">

                <strong>
                    Due Date:
                </strong>

                {{ assignment.due_date }}

            </div>

        {% endif %}

    </div>


    <div class="assignment-actions">

        <a
            href="{{ url_for('dashboard') }}"
            class="btn btn-secondary"
        >
            Back to Dashboard
        </a>

        {% if classroom %}

            <a
                href="{{ url_for(
                    'classroom',
                    classroom_id=classroom.id
                ) }}"
                class="btn"
            >
                Back to Classroom
            </a>

        {% endif %}

    </div>

</div>

{% endblock %}
''',

    # ========================================================
    # CSS
    # ========================================================

    "static/css/style.css": '''/* =========================================================
   GENERAL
   ========================================================= */

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background: #f5f7fb;

    color: #222;

    line-height: 1.6;

    min-height: 100vh;

    display: flex;

    flex-direction: column;
}

.container {
    width: 90%;

    max-width: 1200px;

    margin: 0 auto;
}


/* =========================================================
   NAVBAR
   ========================================================= */

.navbar {
    background: #1e3a8a;

    padding: 18px 0;

    box-shadow:
        0 2px 8px rgba(0, 0, 0, 0.1);
}

.nav-container {
    display: flex;

    justify-content: space-between;

    align-items: center;
}

.logo {
    color: white;

    text-decoration: none;

    font-size: 22px;

    font-weight: bold;
}

.nav-links {
    display: flex;

    gap: 20px;

    align-items: center;
}

.nav-links a {
    color: white;

    text-decoration: none;

    font-weight: 500;
}

.nav-links a:hover {
    text-decoration: underline;
}


/* =========================================================
   MAIN
   ========================================================= */

main.container {
    flex: 1;

    padding-top: 30px;

    padding-bottom: 50px;
}


/* =========================================================
   HERO
   ========================================================= */

.hero {
    background:
        linear-gradient(
            135deg,
            #1e3a8a,
            #2563eb
        );

    color: white;

    border-radius: 15px;

    padding: 80px 30px;

    text-align: center;

    margin-bottom: 40px;
}

.hero-content {
    max-width: 750px;

    margin: 0 auto;
}

.hero h1 {
    font-size: 45px;

    margin-bottom: 20px;
}

.hero p {
    font-size: 19px;

    margin-bottom: 30px;
}

.hero-buttons {
    display: flex;

    justify-content: center;

    gap: 15px;

    flex-wrap: wrap;
}


/* =========================================================
   BUTTONS
   ========================================================= */

.btn {
    display: inline-block;

    background: #2563eb;

    color: white;

    text-decoration: none;

    border: none;

    padding: 11px 20px;

    border-radius: 7px;

    cursor: pointer;

    font-size: 15px;

    font-weight: 600;

    transition: 0.2s;
}

.btn:hover {
    background: #1d4ed8;

    transform: translateY(-1px);
}

.btn-secondary {
    background: #64748b;
}

.btn-secondary:hover {
    background: #475569;
}

.full-width {
    width: 100%;
}


/* =========================================================
   FEATURES
   ========================================================= */

.features {
    display: grid;

    grid-template-columns:
        repeat(3, 1fr);

    gap: 25px;
}

.feature-card {
    background: white;

    padding: 30px;

    border-radius: 12px;

    box-shadow:
        0 3px 12px rgba(0, 0, 0, 0.08);

    text-align: center;
}

.feature-card h3 {
    margin-bottom: 10px;

    color: #1e3a8a;
}


/* =========================================================
   AUTH
   ========================================================= */

.auth-container {
    max-width: 500px;

    margin: 40px auto;
}

.auth-card {
    background: white;

    padding: 35px;

    border-radius: 12px;

    box-shadow:
        0 3px 15px rgba(0, 0, 0, 0.08);
}

.auth-card h2 {
    margin-bottom: 8px;
}

.auth-card > p {
    margin-bottom: 25px;

    color: #666;
}

.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;

    margin-bottom: 7px;

    font-weight: 600;
}

.form-group input,
.form-group select {
    width: 100%;

    padding: 12px;

    border: 1px solid #d1d5db;

    border-radius: 7px;

    font-size: 15px;

    outline: none;
}

.form-group input:focus,
.form-group select:focus {
    border-color: #2563eb;

    box-shadow:
        0 0 0 2px rgba(
            37,
            99,
            235,
            0.1
        );
}

.auth-footer {
    text-align: center;

    margin-top: 20px;
}

.auth-footer a {
    color: #2563eb;

    text-decoration: none;

    font-weight: bold;
}


/* =========================================================
   ALERTS
   ========================================================= */

.alert {
    padding: 14px 18px;

    margin-bottom: 20px;

    border-radius: 7px;

    font-weight: 500;
}

.alert.success {
    background: #dcfce7;

    color: #166534;
}

.alert.danger {
    background: #fee2e2;

    color: #991b1b;
}


/* =========================================================
   DASHBOARD
   ========================================================= */

.dashboard-header {
    background: white;

    padding: 30px;

    border-radius: 12px;

    margin-bottom: 30px;

    box-shadow:
        0 3px 12px rgba(0, 0, 0, 0.06);
}

.dashboard-section {
    margin-bottom: 40px;
}

.dashboard-section h2 {
    margin-bottom: 20px;

    color: #1e3a8a;
}

.card-grid {
    display: grid;

    grid-template-columns:
        repeat(3, 1fr);

    gap: 20px;
}

.classroom-card {
    background: white;

    padding: 25px;

    border-radius: 10px;

    box-shadow:
        0 3px 12px rgba(0, 0, 0, 0.07);
}

.classroom-card h3 {
    margin-bottom: 10px;

    color: #1e3a8a;
}

.classroom-card p {
    margin-bottom: 20px;

    color: #555;
}


/* =========================================================
   ASSIGNMENTS
   ========================================================= */

.assignment-list {
    display: flex;

    flex-direction: column;

    gap: 15px;
}

.assignment-card {
    background: white;

    padding: 22px;

    border-radius: 10px;

    box-shadow:
        0 3px 12px rgba(0, 0, 0, 0.06);

    display: flex;

    justify-content: space-between;

    align-items: center;

    gap: 20px;
}

.assignment-card h3 {
    color: #1e3a8a;

    margin-bottom: 5px;
}

.assignment-card p {
    color: #555;
}

.assignment-card small {
    display: block;

    margin-top: 8px;

    color: #666;
}

.assignment-detail {
    background: white;

    border-radius: 12px;

    padding: 35px;

    box-shadow:
        0 3px 15px rgba(0, 0, 0, 0.07);
}

.assignment-header {
    border-bottom:
        1px solid #e5e7eb;

    padding-bottom: 25px;

    margin-bottom: 25px;
}

.assignment-header h1 {
    margin: 10px 0;
}

.assignment-content h2 {
    margin-bottom: 10px;

    color: #1e3a8a;
}

.due-date {
    margin-top: 25px;

    padding: 15px;

    background: #eff6ff;

    border-radius: 7px;
}

.assignment-actions {
    margin-top: 30px;

    display: flex;

    gap: 10px;

    flex-wrap: wrap;
}


/* =========================================================
   CLASSROOM
   ========================================================= */

.classroom-header {
    background: #1e3a8a;

    color: white;

    padding: 40px;

    border-radius: 12px;

    margin-bottom: 30px;
}

.classroom-header h1 {
    margin-bottom: 10px;
}

.back-link {
    display: inline-block;

    margin-top: 20px;

    color: #2563eb;

    text-decoration: none;

    font-weight: 600;
}


/* =========================================================
   EMPTY STATE
   ========================================================= */

.empty-state {
    background: white;

    padding: 30px;

    border-radius: 10px;

    text-align: center;

    color: #666;
}


/* =========================================================
   BADGE
   ========================================================= */

.badge {
    display: inline-block;

    background: #dbeafe;

    color: #1e40af;

    padding: 5px 10px;

    border-radius: 20px;

    font-size: 13px;

    font-weight: bold;
}


/* =========================================================
   FOOTER
   ========================================================= */

footer {
    background: #111827;

    color: #d1d5db;

    text-align: center;

    padding: 20px;

    margin-top: auto;
}


/* =========================================================
   RESPONSIVE DESIGN
   ========================================================= */

@media (max-width: 800px) {

    .features {
        grid-template-columns: 1fr;
    }

    .card-grid {
        grid-template-columns: 1fr;
    }

    .hero h1 {
        font-size: 35px;
    }

    .nav-container {
        flex-direction: column;

        gap: 15px;
    }

    .assignment-card {
        flex-direction: column;

        align-items: flex-start;
    }
}


@media (max-width: 500px) {

    .nav-links {
        gap: 10px;

        flex-wrap: wrap;

        justify-content: center;
    }

    .hero {
        padding: 50px 20px;
    }

    .hero h1 {
        font-size: 30px;
    }

    .auth-card {
        padding: 25px;
    }
}
'''
}


# ============================================================
# CREATE DIRECTORIES AND FILES
# ============================================================

print("\nCreating Virtual Classroom project...")
print("=" * 55)

for relative_path, content in files.items():

    file_path = os.path.join(
        PROJECT_ROOT,
        relative_path
    )

    directory = os.path.dirname(file_path)

    # Create directory if it does not exist
    if directory:
        os.makedirs(
            directory,
            exist_ok=True
        )

    # Create/write file
    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(content)

    print(f"[CREATED] {relative_path}")


# ============================================================
# FINISHED
# ============================================================

print("=" * 55)

print("\nProject created successfully!")

print("\nProject location:")
print(PROJECT_ROOT)

print("\nStructure:")

print("""
virtual-classroom/
├── .env
├── app.py
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── classroom.html
│   └── assignment.html
└── static/
    └── css/
        └── style.css
""")

print("\nNext steps:")
print("1. Open a terminal in this folder.")
print("2. Create a virtual environment.")
print("3. Activate the virtual environment.")
print("4. Install requirements.txt.")
print("5. Run: python app.py")
print("6. Open: http://127.0.0.1:5000")
print()