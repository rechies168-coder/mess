from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# Создаем приложение
app = Flask(__name__)
app.config['SECRET_KEY'] = 'imsitchat_secret_key_123'  # Ключ для сессий
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Создаем базу данных
db = SQLAlchemy(app)


# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)  # Храним открыто (для простоты!)


# Модель сообщения
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(80))  # Денормализация для простоты
    text = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'text': self.text,
            'timestamp': self.timestamp.strftime('%H:%M:%S')
        }


# Создаем таблицы (если их нет)
with app.app_context():
    db.create_all()


# Главная страница
@app.route('/')
def index():
    return render_template('index.html')


# API: Регистрация
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Заполните все поля'}), 400

    # Проверяем, есть ли уже такой пользователь
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Пользователь уже существует'}), 400

    # Создаем пользователя
    user = User(username=username, password=password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'success': True, 'username': username})


# API: Вход
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return jsonify({'error': 'Неверное имя или пароль'}), 400

    session['user_id'] = user.id
    session['username'] = user.username

    return jsonify({'success': True, 'username': username})


# API: Выход
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


# API: Проверка авторизации
@app.route('/api/me', methods=['GET'])
def me():
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'username': session['username']
        })
    return jsonify({'authenticated': False})


# API: Отправка сообщения
@app.route('/api/messages', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401

    data = request.json
    text = data.get('text', '').strip()

    if not text:
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400

    message = Message(
        user_id=session['user_id'],
        username=session['username'],
        text=text
    )
    db.session.add(message)
    db.session.commit()

    return jsonify({'success': True, 'message': message.to_dict()})


# API: Получение всех сообщений
@app.route('/api/messages', methods=['GET'])
def get_messages():
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    return jsonify([m.to_dict() for m in messages])


# API: Получение новых сообщений (с момента последнего ID)
@app.route('/api/messages/after/<int:last_id>', methods=['GET'])
def get_messages_after(last_id):
    messages = Message.query.filter(Message.id > last_id).order_by(Message.timestamp.asc()).all()
    return jsonify([m.to_dict() for m in messages])


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)