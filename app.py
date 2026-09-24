# ============================================================
# 🌐 Force IPv4 (fixes SSL handshake timeout with Supabase)
# This MUST be the very first thing that runs, before any
# other imports that might use sockets (httpx, supabase, etc.)
# ============================================================
import socket

_original_getaddrinfo = socket.getaddrinfo

def _ipv4_only_getaddrinfo(*args, **kwargs):
    responses = _original_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET]

socket.getaddrinfo = _ipv4_only_getaddrinfo
# ============================================================

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from supabase import create_client, Client
from dotenv import load_dotenv
from functools import wraps
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
# Using threading mode to work with gunicorn gthread worker on Render
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ============================================================
# 🔌 SUPABASE CLIENT INITIALIZATION
# ============================================================
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# Clean the URL and key (removes quotes, spaces, trailing slashes)
if url:
    url = url.strip().strip("'").strip('"')
    if url.endswith("/"):
        url = url[:-1]
    if not url.startswith("https://"):
        url = "https://" + url

if key:
    key = key.strip().strip("'").strip('"')

# Debug print
print("\n" + "="*50)
print(f"DEBUG: Supabase URL is: '{url}'")
print(f"DEBUG: Supabase Key starts with: '{key[:10] if key else 'None'}...'")
print("="*50 + "\n")

supabase: Client = create_client(url, key)


# ============================================================
# 🔐 AUTHENTICATION DECORATOR
# ============================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# 🏠 HOME / INDEX
# ============================================================
@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


# ============================================================
# 📝 REGISTER
# ============================================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role', 'student')

        try:
            # Create user in Supabase Auth
            # Metadata (full_name, role) is picked up by the Postgres
            # trigger 'handle_new_user' which auto-creates the profile row.
            user = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name,
                        "role": role
                    }
                }
            })

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Registration error: {str(e)}', 'danger')
    return render_template('register.html')


# ============================================================
# 🔑 LOGIN (with self-healing profile creation)
# ============================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            session['user'] = {
                'id': response.user.id,
                'email': response.user.email,
                'access_token': response.session.access_token
            }

            # Fetch profile — with self-healing fallback if it's missing
            try:
                profile = supabase.table('profiles').select('*').eq('id', response.user.id).single().execute()
                profile_data = profile.data
            except Exception:
                # Profile doesn't exist — create it now
                meta = response.user.user_metadata or {}
                profile_data = {
                    "id": response.user.id,
                    "full_name": meta.get('full_name', 'User'),
                    "role": meta.get('role', 'student')
                }
                supabase.table('profiles').insert(profile_data).execute()

            session['profile'] = profile_data
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Login error: {str(e)}', 'danger')
    return render_template('login.html')


# ============================================================
# 🚪 LOGOUT
# ============================================================
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ============================================================
# 📊 DASHBOARD (Teacher + Student views)
# ============================================================
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user']['id']
    role = session['profile']['role']

    if role == 'teacher':
        # Teacher sees classrooms they created
        classrooms = supabase.table('classrooms').select('*').eq('teacher_id', user_id).execute()
        enrolled_classrooms = classrooms.data
        available_classrooms = []
    else:
        # Student sees classrooms they're enrolled in
        enrollments = supabase.table('enrollments').select('classroom_id, classrooms(*)').eq('student_id', user_id).execute()
        enrolled_classrooms = [e['classrooms'] for e in enrollments.data if e.get('classrooms')]

        # Get IDs of classrooms they're already in
        enrolled_ids = [e['classroom_id'] for e in enrollments.data]

        # Get all classrooms they're NOT enrolled in
        all_classrooms = supabase.table('classrooms').select('*, profiles(full_name)').execute()
        available_classrooms = [c for c in all_classrooms.data if c['id'] not in enrolled_ids]

    return render_template(
        'dashboard.html',
        classrooms=enrolled_classrooms,
        available_classrooms=available_classrooms,
        role=role
    )


# ============================================================
# 🏫 CLASSROOM VIEW
# ============================================================
@app.route('/classroom/<int:classroom_id>')
@login_required
def classroom(classroom_id):
    classroom = supabase.table('classrooms').select('*').eq('id', classroom_id).single().execute()
    announcements = supabase.table('announcements').select('*, profiles(full_name)').eq('classroom_id', classroom_id).order('created_at', desc=True).execute()
    assignments = supabase.table('assignments').select('*').eq('classroom_id', classroom_id).order('due_date', desc=True).execute()
    messages = supabase.table('messages').select('*, profiles(full_name)').eq('classroom_id', classroom_id).order('created_at', desc=True).limit(50).execute()

    return render_template('classroom.html',
                         classroom=classroom.data,
                         announcements=announcements.data,
                         assignments=assignments.data,
                         messages=messages.data[::-1])


# ============================================================
# ➕ CREATE CLASSROOM (Teacher only)
# ============================================================
@app.route('/create_classroom', methods=['POST'])
@login_required
def create_classroom():
    if session['profile']['role'] != 'teacher':
        flash('Only teachers can create classrooms.', 'danger')
        return redirect(url_for('dashboard'))

    name = request.form.get('name')
    description = request.form.get('description')
    teacher_id = session['user']['id']

    try:
        supabase.table('classrooms').insert({
            "name": name,
            "description": description,
            "teacher_id": teacher_id
        }).execute()
        flash('Classroom created!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')

    return redirect(url_for('dashboard'))


# ============================================================
# ✅ ENROLL IN CLASSROOM (Student)
# ============================================================
@app.route('/enroll/<int:classroom_id>', methods=['POST'])
@login_required
def enroll(classroom_id):
    student_id = session['user']['id']
    try:
        supabase.table('enrollments').insert({
            "classroom_id": classroom_id,
            "student_id": student_id
        }).execute()
        flash('Enrolled successfully!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('dashboard'))


# ============================================================
# ❌ UNENROLL FROM CLASSROOM (Student)
# ============================================================
@app.route('/unenroll/<int:classroom_id>', methods=['POST'])
@login_required
def unenroll(classroom_id):
    student_id = session['user']['id']
    try:
        supabase.table('enrollments').delete().eq('classroom_id', classroom_id).eq('student_id', student_id).execute()
        flash('Left the classroom.', 'info')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('dashboard'))


# ============================================================
# 📢 POST ANNOUNCEMENT (Teacher only)
# ============================================================
@app.route('/post_announcement/<int:classroom_id>', methods=['POST'])
@login_required
def post_announcement(classroom_id):
    if session['profile']['role'] != 'teacher':
        flash('Only teachers can post announcements.', 'danger')
        return redirect(url_for('classroom', classroom_id=classroom_id))

    content = request.form.get('content')
    author_id = session['user']['id']

    try:
        supabase.table('announcements').insert({
            "classroom_id": classroom_id,
            "author_id": author_id,
            "content": content
        }).execute()
        flash('Announcement posted!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')

    return redirect(url_for('classroom', classroom_id=classroom_id))


# ============================================================
# 📚 CREATE ASSIGNMENT (Teacher only)
# ============================================================
@app.route('/create_assignment/<int:classroom_id>', methods=['POST'])
@login_required
def create_assignment(classroom_id):
    if session['profile']['role'] != 'teacher':
        flash('Only teachers can create assignments.', 'danger')
        return redirect(url_for('classroom', classroom_id=classroom_id))

    title = request.form.get('title')
    description = request.form.get('description')
    due_date = request.form.get('due_date')

    try:
        supabase.table('assignments').insert({
            "classroom_id": classroom_id,
            "title": title,
            "description": description,
            "due_date": due_date
        }).execute()
        flash('Assignment created!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')

    return redirect(url_for('classroom', classroom_id=classroom_id))


# ============================================================
# 💬 SOCKET.IO EVENTS (Real-time chat)
# ============================================================
@socketio.on('join')
def on_join(data):
    username = session.get('profile', {}).get('full_name', 'Anonymous')
    room = data['room']
    join_room(room)
    emit('status', {'msg': f'{username} has entered the chat.'}, room=room)


@socketio.on('leave')
def on_leave(data):
    username = session.get('profile', {}).get('full_name', 'Anonymous')
    room = data['room']
    leave_room(room)
    emit('status', {'msg': f'{username} has left the chat.'}, room=room)


@socketio.on('send_message')
def handle_message(data):
    room = data['room']
    message = data['message']
    user_id = session['user']['id']
    full_name = session['profile']['full_name']

    try:
        supabase.table('messages').insert({
            "classroom_id": int(room),
            "user_id": user_id,
            "content": message
        }).execute()
    except Exception as e:
        print(f"Error saving message: {e}")

    emit('receive_message', {
        'user': full_name,
        'message': message,
        'timestamp': datetime.now().strftime('%H:%M')
    }, room=room)


# ============================================================
# 🚀 RUN (Only used for local development)
# ============================================================
if __name__ == '__main__':
    socketio.run(app, debug=True, port=5001, allow_unsafe_werkzeug=True)