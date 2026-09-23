import os

# ============================================================
# VIRTUAL CLASSROOM PROJECT GENERATOR
# ============================================================

# The root folder that already exists
ROOT = "virtual-classroom"

# ------------------------------------------------------------
# Project structure
# ------------------------------------------------------------

directories = [
    ROOT,
    os.path.join(ROOT, "templates"),
    os.path.join(ROOT, "static"),
    os.path.join(ROOT, "static", "css"),
]

files = {
    # ========================================================
    # .env
    # ========================================================
    os.path.join(ROOT, ".env"): """SECRET_KEY=change-this-secret-key
FLASK_ENV=development
DATABASE_URL=sqlite:///classroom.db
""",

    # ========================================================
    # requirements.txt
    # ========================================================
    os.path.join(ROOT, "requirements.txt"): """Flask==3.1.2
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
python-dotenv==1.1.1
Werkzeug==3.1.3
""",

    # ========================================================
    # app.py
    # ========================================================
    os.path.join(ROOT, "app.py"): '''import os
from datetime import datetime

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash
)
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


# ============================================================
# Configuration
# ============================================================

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "development-secret-key"
)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///classroom.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# ============================================================
# Extensions
# ============================================================

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ============================================================
# Database Models
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
        default=datetime.utcnow
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

    teacher = db.Column(
        db.String(100),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    due_date = db.Column(
        db.String(50),
        nullable=True
    )

    classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classroom.id"),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# ============================================================
# Login Manager
# ============================================================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ============================================================
# Routes
# ============================================================

@app.route("/")
def index():
    classrooms = Classroom.query.all()

    return render_template(
        "index.html",
        classrooms=classrooms
    )


# ------------------------------------------------------------
# Register
# ------------------------------------------------------------

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
            flash(
                "Please fill in all required fields.",
                "danger"
            )
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            flash(
                "An account with that email already exists.",
                "danger"
            )
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(
            password
        )

        user = User(
            name=name,
            email=email,
            password=hashed_password,
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


# ------------------------------------------------------------
# Login
# ------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

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

            return redirect(url_for("dashboard"))

        flash(
            "Invalid email or password.",
            "danger"
        )

    return render_template("login.html")


# ------------------------------------------------------------
# Logout
# ------------------------------------------------------------

@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(url_for("index"))


# ------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Classroom
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Create Assignment
# ------------------------------------------------------------

@app.route(
    "/assignment/<int:classroom_id>",
    methods=["GET", "POST"]
)
@login_required
def assignment(classroom_id):

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

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        due_date = request.form.get(
            "due_date",
            ""
        ).strip()

        if not title or not description:
            flash(
                "Title and description are required.",
                "danger"
            )
            return redirect(
                url_for(
                    "assignment",
                    classroom_id=classroom_id
                )
            )

        new_assignment = Assignment(
            title=title,
            description=description,
            due_date=due_date,
            classroom_id=classroom_id
        )

        db.session.add(new_assignment)
        db.session.commit()

        flash(
            "Assignment created successfully.",
            "success"
        )

        return redirect(
            url_for(
                "classroom",
                classroom_id=classroom_id
            )
        )

    return render_template(
        "assignment.html",
        classroom=classroom_data
    )


# ============================================================
# Initialize Database
# ============================================================

with app.app_context():
    db.create_all()


# ============================================================
# Run Application
# ============================================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
''',

    # ========================================================
    # templates/base.html
    # ========================================================
    os.path.join(ROOT, "templates", "base.html"): '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>
        {% block title %}
        Virtual Classroom
        {% endblock %}
    </title>

    <link
        rel="stylesheet"
        href="{{ url_for('static', filename='css/style.css') }}"
    >
</head>

<body>

<header class="navbar">

    <div class="container nav-content">

        <a
            href="{{ url_for('index') }}"
            class="logo"
        >
            Virtual Classroom
        </a>

        <nav>

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

        </nav>

    </div>

</header>


<main class="container">

    {% with messages = get_flashed_messages(
        with_categories=true
    ) %}

        {% if messages %}

            {% for category, message in messages %}

                <div class="alert {{ category }}">
                    {{ message }}
                </div>

            {% endfor %}

        {% endif %}

    {% endwith %}


    {% block content %}
    {% endblock %}

</main>


<footer>

    <p>
        &copy; 2026 Virtual Classroom.
        All rights reserved.
    </p>

</footer>

</body>
</html>
''',

    # ========================================================
    # templates/index.html
    # ========================================================
    os.path.join(ROOT, "templates", "index.html"): '''{% extends "base.html" %}

{% block title %}
Home - Virtual Classroom
{% endblock %}

{% block content %}

<section class="hero">

    <div>

        <h1>
            Learn. Connect. Grow.
        </h1>

        <p>
            Welcome to your virtual classroom.
            Learn online, join classrooms,
            and manage your assignments.
        </p>

        {% if current_user.is_authenticated %}

            <a
                href="{{ url_for('dashboard') }}"
                class="btn"
            >
                Go to Dashboard
            </a>

        {% else %}

            <a
                href="{{ url_for('register') }}"
                class="btn"
            >
                Get Started
            </a>

        {% endif %}

    </div>

</section>


<section>

    <h2>Available Classrooms</h2>

    <div class="card-grid">

        {% for classroom in classrooms %}

            <div class="card">

                <h3>
                    {{ classroom.name }}
                </h3>

                <p>
                    {{ classroom.description }}
                </p>

                <p>
                    <strong>Teacher:</strong>
                    {{ classroom.teacher }}
                </p>

                {% if current_user.is_authenticated %}

                    <a
                        href="{{ url_for(
                            'classroom',
                            classroom_id=classroom.id
                        ) }}"
                        class="btn small"
                    >
                        Enter Classroom
                    </a>

                {% endif %}

            </div>

        {% else %}

            <p>
                No classrooms available yet.
            </p>

        {% endfor %}

    </div>

</section>

{% endblock %}
''',

    # ========================================================
    # templates/login.html
    # ========================================================
    os.path.join(ROOT, "templates", "login.html"): '''{% extends "base.html" %}

{% block title %}
Login - Virtual Classroom
{% endblock %}

{% block content %}

<div class="form-container">

    <h1>Login</h1>

    <form method="POST">

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


        <button
            type="submit"
            class="btn"
        >
            Login
        </button>

    </form>

    <p>
        Don't have an account?

        <a href="{{ url_for('register') }}">
            Register here
        </a>
    </p>

</div>

{% endblock %}
''',

    # ========================================================
    # templates/register.html
    # ========================================================
    os.path.join(ROOT, "templates", "register.html"): '''{% extends "base.html" %}

{% block title %}
Register - Virtual Classroom
{% endblock %}

{% block content %}

<div class="form-container">

    <h1>Create Account</h1>

    <form method="POST">

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


        <button
            type="submit"
            class="btn"
        >
            Register
        </button>

    </form>

    <p>
        Already have an account?

        <a href="{{ url_for('login') }}">
            Login here
        </a>
    </p>

</div>

{% endblock %}
''',

    # ========================================================
    # templates/dashboard.html
    # ========================================================
    os.path.join(ROOT, "templates", "dashboard.html"): '''{% extends "base.html" %}

{% block title %}
Dashboard - Virtual Classroom
{% endblock %}

{% block content %}

<section class="dashboard-header">

    <h1>
        Welcome, {{ current_user.name }}
    </h1>

    <p>
        Role: {{ current_user.role|capitalize }}
    </p>

</section>


<section>

    <h2>Your Classrooms</h2>

    <div class="card-grid">

        {% for classroom in classrooms %}

            <div class="card">

                <h3>
                    {{ classroom.name }}
                </h3>

                <p>
                    {{ classroom.description }}
                </p>

                <p>
                    <strong>Teacher:</strong>
                    {{ classroom.teacher }}
                </p>

                <a
                    href="{{ url_for(
                        'classroom',
                        classroom_id=classroom.id
                    ) }}"
                    class="btn small"
                >
                    Open Classroom
                </a>

            </div>

        {% else %}

            <p>
                No classrooms available.
            </p>

        {% endfor %}

    </div>

</section>


<section>

    <h2>Assignments</h2>

    <div class="card-grid">

        {% for assignment in assignments %}

            <div class="card">

                <h3>
                    {{ assignment.title }}
                </h3>

                <p>
                    {{ assignment.description }}
                </p>

                {% if assignment.due_date %}

                    <p>
                        <strong>Due:</strong>
                        {{ assignment.due_date }}
                    </p>

                {% endif %}

            </div>

        {% else %}

            <p>
                No assignments available.
            </p>

        {% endfor %}

    </div>

</section>

{% endblock %}
''',

    # ========================================================
    # templates/classroom.html
    # ========================================================
    os.path.join(ROOT, "templates", "classroom.html"): '''{% extends "base.html" %}

{% block title %}
{{ classroom.name }} - Virtual Classroom
{% endblock %}

{% block content %}

<section class="classroom-header">

    <h1>
        {{ classroom.name }}
    </h1>

    <p>
        {{ classroom.description }}
    </p>

    <p>
        <strong>Teacher:</strong>
        {{ classroom.teacher }}
    </p>

</section>


<section>

    <div class="section-heading">

        <h2>
            Assignments
        </h2>

        {% if current_user.role == "teacher" %}

            <a
                href="{{ url_for(
                    'assignment',
                    classroom_id=classroom.id
                ) }}"
                class="btn"
            >
                Create Assignment
            </a>

        {% endif %}

    </div>


    <div class="card-grid">

        {% for item in assignments %}

            <div class="card">

                <h3>
                    {{ item.title }}
                </h3>

                <p>
                    {{ item.description }}
                </p>

                {% if item.due_date %}

                    <p>
                        <strong>Due:</strong>
                        {{ item.due_date }}
                    </p>

                {% endif %}

            </div>

        {% else %}

            <p>
                No assignments have been posted yet.
            </p>

        {% endfor %}

    </div>

</section>


<a
    href="{{ url_for('dashboard') }}"
    class="back-link"
>
    &larr; Back to Dashboard
</a>

{% endblock %}
''',

    # ========================================================
    # templates/assignment.html
    # ========================================================
    os.path.join(ROOT, "templates", "assignment.html"): '''{% extends "base.html" %}

{% block title %}
Create Assignment - Virtual Classroom
{% endblock %}

{% block content %}

<div class="form-container">

    <h1>
        Create Assignment
    </h1>

    <p>
        Classroom:
        <strong>{{ classroom.name }}</strong>
    </p>

    <form method="POST">

        <label for="title">
            Assignment Title
        </label>

        <input
            type="text"
            id="title"
            name="title"
            placeholder="Enter assignment title"
            required
        >


        <label for="description">
            Description
        </label>

        <textarea
            id="description"
            name="description"
            rows="6"
            placeholder="Enter assignment instructions"
            required
        ></textarea>


        <label for="due_date">
            Due Date
        </label>

        <input
            type="date"
            id="due_date"
            name="due_date"
        >


        <button
            type="submit"
            class="btn"
        >
            Create Assignment
        </button>

    </form>

</div>

{% endblock %}
''',

    # ========================================================
    # static/css/style.css
    # ========================================================
    os.path.join(
        ROOT,
        "static",
        "css",
        "style.css"
    ): '''* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: Arial, Helvetica, sans-serif;
    background: #f4f7fb;
    color: #222;
    line-height: 1.6;
}

.container {
    width: 90%;
    max-width: 1200px;
    margin: auto;
}


/* ==========================================================
   Navbar
   ========================================================== */

.navbar {
    background: #1e293b;
    color: white;
    padding: 18px 0;
}

.nav-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.logo {
    color: white;
    text-decoration: none;
    font-size: 1.4rem;
    font-weight: bold;
}

nav {
    display: flex;
    gap: 20px;
}

nav a {
    color: white;
    text-decoration: none;
}

nav a:hover {
    text-decoration: underline;
}


/* ==========================================================
   Main
   ========================================================== */

main {
    min-height: 80vh;
    padding-top: 40px;
    padding-bottom: 40px;
}

h1,
h2,
h3 {
    margin-bottom: 15px;
}


/* ==========================================================
   Hero
   ========================================================== */

.hero {
    background: white;
    padding: 70px 40px;
    margin-bottom: 40px;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.hero h1 {
    font-size: 2.8rem;
}

.hero p {
    max-width: 700px;
    margin: 0 auto 25px;
}


/* ==========================================================
   Buttons
   ========================================================== */

.btn {
    display: inline-block;
    background: #2563eb;
    color: white;
    padding: 11px 20px;
    border: none;
    border-radius: 6px;
    text-decoration: none;
    cursor: pointer;
    font-size: 1rem;
}

.btn:hover {
    background: #1d4ed8;
}

.btn.small {
    padding: 8px 14px;
    font-size: 0.9rem;
}


/* ==========================================================
   Cards
   ========================================================== */

.card-grid {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(260px, 1fr));

    gap: 20px;
    margin-top: 20px;
    margin-bottom: 40px;
}

.card {
    background: white;
    padding: 25px;
    border-radius: 10px;
    box-shadow:
        0 3px 12px rgba(0, 0, 0, 0.07);
}

.card p {
    margin-bottom: 12px;
}


/* ==========================================================
   Forms
   ========================================================== */

.form-container {
    background: white;
    width: 100%;
    max-width: 550px;
    margin: 20px auto;
    padding: 35px;
    border-radius: 10px;
    box-shadow:
        0 4px 18px rgba(0, 0, 0, 0.08);
}

.form-container form {
    display: flex;
    flex-direction: column;
}

.form-container label {
    margin-top: 15px;
    margin-bottom: 6px;
    font-weight: bold;
}

.form-container input,
.form-container select,
.form-container textarea {
    width: 100%;
    padding: 12px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-size: 1rem;
}

.form-container textarea {
    resize: vertical;
}

.form-container button {
    margin-top: 25px;
}


/* ==========================================================
   Alerts
   ========================================================== */

.alert {
    padding: 12px 18px;
    margin-bottom: 20px;
    border-radius: 6px;
}

.alert.success {
    background: #dcfce7;
    color: #166534;
}

.alert.danger {
    background: #fee2e2;
    color: #991b1b;
}


/* ==========================================================
   Dashboard / Classroom
   ========================================================== */

.dashboard-header,
.classroom-header {
    background: white;
    padding: 30px;
    margin-bottom: 30px;
    border-radius: 10px;
}

.section-heading {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
    margin-bottom: 20px;
}

.back-link {
    display: inline-block;
    margin-top: 20px;
    color: #2563eb;
    text-decoration: none;
}


/* ==========================================================
   Footer
   ========================================================== */

footer {
    background: #1e293b;
    color: white;
    text-align: center;
    padding: 25px;
}


/* ==========================================================
   Responsive
   ========================================================== */

@media (max-width: 700px) {

    .nav-content {
        flex-direction: column;
        gap: 15px;
    }

    nav {
        flex-wrap: wrap;
        justify-content: center;
    }

    .hero h1 {
        font-size: 2rem;
    }

    .hero {
        padding: 45px 20px;
    }

    .section-heading {
        flex-direction: column;
        align-items: flex-start;
    }
}
'''
}


# ============================================================
# CREATE DIRECTORIES
# ============================================================

for directory in directories:
    os.makedirs(directory, exist_ok=True)


# ============================================================
# CREATE FILES
# ============================================================

for file_path, content in files.items():

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(content)


# ============================================================
# FINISHED
# ============================================================

print()
print("=" * 60)
print("VIRTUAL CLASSROOM PROJECT CREATED SUCCESSFULLY")
print("=" * 60)
print()

for file_path in files:
    print(f"Created: {file_path}")

print()
print("Project structure:")
print()
print("virtual-classroom/")
print("├── .env")
print("├── app.py")
print("├── requirements.txt")
print("├── templates/")
print("│   ├── base.html")
print("│   ├── index.html")
print("│   ├── login.html")
print("│   ├── register.html")
print("│   ├── dashboard.html")
print("│   ├── classroom.html")
print("│   └── assignment.html")
print("└── static/")
print("    └── css/")
print("        └── style.css")
print()
print("Next steps:")
print("1. cd virtual-classroom")
print("2. Create/activate a virtual environment")
print("3. pip install -r requirements.txt")
print("4. python app.py")
print("5. Open http://127.0.0.1:5000")
print()
print("=" * 60)