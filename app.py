import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'imsit_pro_999'
# Подключение к Postgres (без пароля)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres@localhost:5432/chat_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# --- МОДЕЛИ ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(255), default='/static/default_avatar.png')

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

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter((User.username == data['username']) | (User.email == data['email'])).first():
        return jsonify({'error': 'Логин или Email заняты'}), 400
    user = User(username=data['username'], email=data['email'],
                password_hash=generate_password_hash(data['password']))
    db.session.add(user); db.session.commit()
    return jsonify({'success': True})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password_hash, data['password']):
        session['user_id'] = user.id
        session['username'] = user.username
        return jsonify({'success': True})
    return jsonify({'error': 'Ошибка входа'}), 401

@app.route('/api/me')
def me():
    u = User.query.get(session['user_id'])
    return jsonify({'username': u.username, 'avatar': u.avatar_url, 'email': u.email})


@app.route('/api/profile/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session: return jsonify({'error': 'unauth'}), 401
    user = User.query.get(session['user_id'])

    if 'avatar' in request.files:
        file = request.files['avatar']
        if file.filename != '':
            # 1. Получаем расширение оригинального файла (jpg, png, и т.д.)
            ext = file.filename.rsplit('.', 1)[1].lower()

            # 2. Проверяем, что это именно картинка
            if ext not in ['jpg', 'jpeg', 'png', 'gif']:
                return jsonify({'error': 'Неверный формат файла'}), 400

            # 3. Генерируем имя файла с ПРАВИЛЬНЫМ расширением
            filename = secure_filename(f"av_{user.id}_{int(datetime.now().timestamp())}.{ext}")

            # 4. Сохраняем
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # 5. Обновляем путь в базе данных
            user.avatar_url = '/static/uploads/' + filename
            db.session.commit()

            return jsonify({'success': True, 'avatar_url': user.avatar_url})

    return jsonify({'error': 'No file'}), 400

@app.route('/api/users/search')
def search():
    q = request.args.get('q', '')
    users = User.query.filter(User.username.ilike(f'%{q}%')).all()
    return jsonify([{'username': u.username, 'avatar': u.avatar_url} for u in users])

@app.route('/api/chat/start/<target_user>', methods=['POST'])
def start_chat(target_user):
    me = User.query.get(session['user_id'])
    other = User.query.filter_by(username=target_user).first()
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
def messages(room_id):
    if request.method == 'POST':
        v_url = None
        if 'voice' in request.files:
            file = request.files['voice']
            fname = secure_filename(f"v_{datetime.now().timestamp()}.webm")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            v_url = '/static/uploads/' + fname
        msg = Message(room_id=room_id, user_id=session['user_id'], username=session['username'],
                      text=request.form.get('text'), voice_url=v_url)
        db.session.add(msg); db.session.commit()
        return jsonify({'success': True})
    msgs = Message.query.filter_by(room_id=room_id).all()
    return jsonify([{'username': m.username, 'text': m.text, 'voice': m.voice_url, 'time': m.timestamp.strftime('%H:%M')} for m in msgs])

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True)