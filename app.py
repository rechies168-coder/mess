import os
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'imsit_pro_ultra_999'

# --- ПОДКЛЮЧЕНИЕ POSTGRES (Пароль 123) ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:123@localhost:5432/chat_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# --- МОДЕЛИ ДАННЫХ ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(255), default='/static/default_avatar.png')
    bio = db.Column(db.String(255), default='Привет! Я в iMSITChat.')

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    is_private = db.Column(db.Boolean, default=True)
    members = db.relationship('User', secondary='room_members', backref='rooms')

room_members = db.Table('room_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('room_id', db.Integer, db.ForeignKey('room.id'))
)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    username = db.Column(db.String(80))
    text = db.Column(db.Text)
    voice_url = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- МАРШРУТЫ ---
@app.route('/')
def index():
    if 'user_id' not in session: return redirect('/login')
    return render_template('index.html')

@app.route('/login')
def login_page(): return render_template('login.html')

@app.route('/register')
def register_page(): return render_template('register.html')

# --- API АВТОРИЗАЦИИ С ВАЛИДАЦИЕЙ ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    user = data.get('username', '').strip()
    email = data.get('email', '').strip()
    pwd = data.get('password', '')

    if len(user) < 3: return jsonify({'error': 'Логин слишком короткий'}), 400
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email): return jsonify({'error': 'Неверный формат Email'}), 400
    if len(pwd) < 6: return jsonify({'error': 'Пароль слишком короткий (мин. 6)'}), 400

    if User.query.filter((User.username == user) | (User.email == email)).first():
        return jsonify({'error': 'Логин или Email уже заняты'}), 400

    new_user = User(username=user, email=email, password_hash=generate_password_hash(pwd))
    db.session.add(new_user); db.session.commit()
    return jsonify({'success': True})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    u = User.query.filter_by(username=data['username']).first()
    if u and check_password_hash(u.password_hash, data['password']):
        session['user_id'] = u.id; session['username'] = u.username
        return jsonify({'success': True})
    return jsonify({'error': 'Неверный логин или пароль'}), 401

# --- API ПРОФИЛЯ ---
@app.route('/api/me')
def get_me():
    u = User.query.get(session['user_id'])
    return jsonify({'username': u.username, 'avatar': u.avatar_url, 'bio': u.bio, 'email': u.email})

@app.route('/api/profile/update', methods=['POST'])
def update_profile():
    u = User.query.get(session['user_id'])
    if 'bio' in request.form: u.bio = request.form['bio'][:255]
    if 'avatar' in request.files:
        file = request.files['avatar']
        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext in ['jpg', 'jpeg', 'png', 'gif']:
            fname = secure_filename(f"av_{u.id}_{int(datetime.now().timestamp())}.{ext}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            u.avatar_url = '/static/uploads/' + fname
    db.session.commit()
    return jsonify({'success': True, 'avatar_url': u.avatar_url})

# --- API ПОИСКА И СООБЩЕНИЙ ---
@app.route('/api/users/search')
def search():
    q = request.args.get('q', '')
    users = User.query.filter(User.username.ilike(f'%{q}%')).all()
    return jsonify([{'username': u.username, 'avatar': u.avatar_url} for u in users])

@app.route('/api/chat/start/<target>', methods=['POST'])
def start_chat(target):
    me = User.query.get(session['user_id'])
    other = User.query.filter_by(username=target).first()
    room = Room.query.filter(Room.members.contains(me), Room.members.contains(other)).first()
    if not room:
        room = Room(name=other.username)
        room.members.extend([me, other])
        db.session.add(room); db.session.commit()
    return jsonify({'room_id': room.id, 'name': other.username, 'avatar': other.avatar_url})

@app.route('/api/rooms')
def get_rooms():
    u = User.query.get(session['user_id'])
    res = []
    for r in u.rooms:
        other = next((m for m in r.members if m.id != u.id), u)
        res.append({'id': r.id, 'name': other.username, 'avatar': other.avatar_url})
    return jsonify(res)

@app.route('/api/messages/<int:room_id>', methods=['GET', 'POST'])
def handle_msgs(room_id):
    if request.method == 'POST':
        v_url = None
        if 'voice' in request.files:
            f = request.files['voice']
            fn = secure_filename(f"v_{datetime.now().timestamp()}.webm")
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], fn))
            v_url = '/static/uploads/' + fn
        m = Message(room_id=room_id, user_id=session['user_id'], username=session['username'],
                    text=request.form.get('text'), voice_url=v_url)
        db.session.add(m); db.session.commit()
        return jsonify({'success': True})
    msgs = Message.query.filter_by(room_id=room_id).order_by(Message.timestamp.asc()).all()
    return jsonify([{'username': m.username, 'text': m.text, 'voice': m.voice_url, 'time': m.timestamp.strftime('%H:%M')} for m in msgs])

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True, port=5000)