# filename="user_management.py"
# Модуль для управления пользователями и верификации email
# Module for user management and email verification

import json
import os
import hashlib
import secrets
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

# ============================================================================
# КОНФИГУРАЦИЯ / CONFIGURATION
# ============================================================================

# Email настройки / Email settings
EMAIL_CONFIG = {
    'smtp_server': 'smtp.beget.com',
    'smtp_port': 465,
    'sender_email': 'strogholod@strogholod.ru',
    'sender_password': 'o5Zeq9Nx*ARo',
    'sender_name': 'Avito Management System'
}

# Настройки верификации / Verification settings
VERIFICATION_CONFIG = {
    'code_length': 6,
    'code_expiry_hours': 24,
    'max_attempts': 3
}

# Путь к файлу пользователей / Users file path
USERS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'users', 'users.json')

# ============================================================================
# УТИЛИТЫ / UTILITIES
# ============================================================================

def ensure_users_file():
    """Создает файл пользователей если он не существует / Creates users file if it doesn't exist"""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def load_users() -> List[Dict]:
    """Загружает список пользователей из файла / Loads users list from file"""
    ensure_users_file()
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_users(users: List[Dict]) -> bool:
    """Сохраняет список пользователей в файл / Saves users list to file"""
    try:
        ensure_users_file()
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"Ошибка сохранения пользователей: {e}")
        return False

def hash_password(password: str) -> str:
    """Хеширует пароль с солью / Hashes password with salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}:{password_hash.hex()}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Проверяет пароль против хеша / Verifies password against hash"""
    try:
        salt, stored_hash = hashed_password.split(':')
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return password_hash.hex() == stored_hash
    except ValueError:
        return False

def generate_verification_code() -> str:
    """Генерирует код верификации / Generates verification code"""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(VERIFICATION_CONFIG['code_length']))

def is_code_expired(created_at: str) -> bool:
    """Проверяет истек ли код верификации / Checks if verification code is expired"""
    try:
        created_time = datetime.fromisoformat(created_at)
        expiry_time = created_time + timedelta(hours=VERIFICATION_CONFIG['code_expiry_hours'])
        return datetime.now() > expiry_time
    except ValueError:
        return True

# ============================================================================
# EMAIL ФУНКЦИИ / EMAIL FUNCTIONS
# ============================================================================

def send_verification_email(user_email: str, username: str, verification_code: str) -> Tuple[bool, str]:
    """
    Отправляет email с кодом верификации / Sends verification email with code
    
    Args:
        user_email: Email пользователя / User's email
        username: Имя пользователя / Username
        verification_code: Код верификации / Verification code
    
    Returns:
        Tuple[bool, str]: (успех, сообщение) / (success, message)
    """
    try:
        # Создаем сообщение / Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{EMAIL_CONFIG['sender_name']} <{EMAIL_CONFIG['sender_email']}>"
        msg['To'] = user_email
        msg['Subject'] = "Подтверждение регистрации - Avito Management"
        
        # HTML версия письма / HTML version of email
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Подтверждение регистрации</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f4f4f4;
                }}
                .container {{
                    background: linear-gradient(135deg, #FF8C42 0%, #C8A2C8 100%);
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: bold;
                    color: white;
                    margin-bottom: 10px;
                }}
                .content {{
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 16px;
                    padding: 30px;
                    margin-bottom: 20px;
                }}
                .verification-code {{
                    background: linear-gradient(135deg, #FF8C42 0%, #C8A2C8 100%);
                    color: white;
                    font-size: 32px;
                    font-weight: bold;
                    text-align: center;
                    padding: 20px;
                    border-radius: 12px;
                    letter-spacing: 4px;
                    margin: 20px 0;
                    font-family: 'Courier New', monospace;
                }}
                .footer {{
                    text-align: center;
                    color: rgba(255, 255, 255, 0.8);
                    font-size: 14px;
                }}
                .warning {{
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    color: #856404;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🏢 Avito Management</div>
                </div>
                
                <div class="content">
                    <h2>Добро пожаловать, {username}!</h2>
                    
                    <p>Спасибо за регистрацию в системе управления Avito. Для завершения регистрации необходимо подтвердить ваш email адрес.</p>
                    
                    <p><strong>Ваш код подтверждения:</strong></p>
                    <div class="verification-code">{verification_code}</div>
                    
                    <div class="warning">
                        <strong>⚠️ Важно:</strong>
                        <ul>
                            <li>Код действителен в течение {VERIFICATION_CONFIG['code_expiry_hours']} часов</li>
                            <li>Не передавайте этот код третьим лицам</li>
                            <li>Если вы не регистрировались в системе, проигнорируйте это письмо</li>
                        </ul>
                    </div>
                    
                    <p>Введите этот код в форме подтверждения для активации вашего аккаунта.</p>
                </div>
                
                <div class="footer">
                    <p>Это письмо отправлено автоматически, не отвечайте на него.</p>
                    <p>© 2024 Avito Management System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Текстовая версия письма / Text version of email
        text_content = f"""
        Добро пожаловать в Avito Management System!
        
        Здравствуйте, {username}!
        
        Спасибо за регистрацию в системе управления Avito. 
        Для завершения регистрации необходимо подтвердить ваш email адрес.
        
        Ваш код подтверждения: {verification_code}
        
        Код действителен в течение {VERIFICATION_CONFIG['code_expiry_hours']} часов.
        
        Введите этот код в форме подтверждения для активации вашего аккаунта.
        
        Если вы не регистрировались в системе, проигнорируйте это письмо.
        
        ---
        Avito Management System
        """
        
        # Добавляем содержимое / Add content
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        # Отправляем email / Send email
        with smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
        
        logging.info(f"Код верификации отправлен на {user_email}")
        return True, "Код верификации отправлен на указанный email"
        
    except Exception as e:
        error_msg = f"Ошибка отправки email: {str(e)}"
        logging.error(error_msg)
        return False, error_msg

# ============================================================================
# УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ / USER MANAGEMENT
# ============================================================================

def register_user(username: str, email: str, password: str) -> Tuple[bool, str]:
    """
    Регистрирует нового пользователя / Registers new user
    
    Args:
        username: Имя пользователя / Username
        email: Email пользователя / User's email
        password: Пароль / Password
    
    Returns:
        Tuple[bool, str]: (успех, сообщение) / (success, message)
    """
    try:
        # Валидация входных данных / Validate input data
        if not username or len(username) < 3 or len(username) > 20:
            return False, "Имя пользователя должно содержать от 3 до 20 символов"
        
        if not email or '@' not in email:
            return False, "Введите корректный email адрес"
        
        if not password or len(password) < 6:
            return False, "Пароль должен содержать минимум 6 символов"
        
        # Проверяем существующих пользователей / Check existing users
        users = load_users()
        
        # Проверяем уникальность имени пользователя / Check username uniqueness
        if any(user['username'].lower() == username.lower() for user in users):
            return False, "Пользователь с таким именем уже существует"
        
        # Проверяем уникальность email / Check email uniqueness
        if any(user['email'].lower() == email.lower() for user in users):
            return False, "Пользователь с таким email уже зарегистрирован"
        
        # Генерируем код верификации / Generate verification code
        verification_code = generate_verification_code()
        current_time = datetime.now().isoformat()
        
        # Создаем пользователя / Create user
        user_data = {
            'id': secrets.token_hex(16),
            'username': username,
            'email': email.lower(),
            'password_hash': hash_password(password),
            'verified': False,
            'verification_code': verification_code,
            'verification_attempts': 0,
            'created_at': current_time,
            'verified_at': None,
            'last_login': None
        }
        
        # Добавляем пользователя / Add user
        users.append(user_data)
        
        if not save_users(users):
            return False, "Ошибка сохранения данных пользователя"
        
        # Отправляем email с кодом / Send verification email
        email_success, email_message = send_verification_email(email, username, verification_code)
        
        if not email_success:
            # Удаляем пользователя если email не отправился / Remove user if email failed
            users = [u for u in users if u['id'] != user_data['id']]
            save_users(users)
            return False, f"Ошибка отправки email: {email_message}"
        
        logging.info(f"Пользователь {username} зарегистрирован, код отправлен на {email}")
        return True, "Регистрация успешна. Проверьте email для подтверждения аккаунта"
        
    except Exception as e:
        error_msg = f"Ошибка регистрации: {str(e)}"
        logging.error(error_msg)
        return False, error_msg

def verify_user_email(email: str, verification_code: str) -> Tuple[bool, str]:
    """
    Верифицирует email пользователя / Verifies user's email
    
    Args:
        email: Email пользователя / User's email
        verification_code: Код верификации / Verification code
    
    Returns:
        Tuple[bool, str]: (успех, сообщение) / (success, message)
    """
    try:
        users = load_users()
        
        # Ищем пользователя / Find user
        user = None
        user_index = -1
        for i, u in enumerate(users):
            if u['email'].lower() == email.lower():
                user = u
                user_index = i
                break
        
        if not user:
            return False, "Пользователь с таким email не найден"
        
        # Проверяем статус верификации / Check verification status
        if user['verified']:
            return False, "Email уже подтвержден"
        
        # Проверяем количество попыток / Check attempts count
        if user['verification_attempts'] >= VERIFICATION_CONFIG['max_attempts']:
            return False, "Превышено максимальное количество попыток верификации"
        
        # Проверяем срок действия кода / Check code expiry
        if is_code_expired(user['created_at']):
            return False, "Код верификации истек. Запросите новый код"
        
        # Проверяем код / Verify code
        if user['verification_code'].upper() != verification_code.upper():
            # Увеличиваем счетчик попыток / Increment attempts counter
            users[user_index]['verification_attempts'] += 1
            save_users(users)
            
            remaining_attempts = VERIFICATION_CONFIG['max_attempts'] - users[user_index]['verification_attempts']
            if remaining_attempts > 0:
                return False, f"Неверный код. Осталось попыток: {remaining_attempts}"
            else:
                return False, "Превышено максимальное количество попыток верификации"
        
        # Верифицируем пользователя / Verify user
        users[user_index]['verified'] = True
        users[user_index]['verified_at'] = datetime.now().isoformat()
        users[user_index]['verification_code'] = None  # Удаляем код после верификации / Remove code after verification
        
        if not save_users(users):
            return False, "Ошибка сохранения данных"
        
        logging.info(f"Email {email} успешно верифицирован")
        return True, "Email успешно подтвержден. Теперь вы можете войти в систему"
        
    except Exception as e:
        error_msg = f"Ошибка верификации: {str(e)}"
        logging.error(error_msg)
        return False, error_msg

def authenticate_user(username: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Аутентифицирует пользователя / Authenticates user
    
    Args:
        username: Имя пользователя или email / Username or email
        password: Пароль / Password
    
    Returns:
        Tuple[bool, str, Optional[Dict]]: (успех, сообщение, данные пользователя) / (success, message, user_data)
    """
    try:
        users = load_users()
        
        # Ищем пользователя по имени или email / Find user by username or email
        user = None
        for u in users:
            if u['username'].lower() == username.lower() or u['email'].lower() == username.lower():
                user = u
                break
        
        if not user:
            return False, "Неверное имя пользователя или пароль", None
        
        # Проверяем верификацию / Check verification
        if not user['verified']:
            return False, "Email не подтвержден. Проверьте почту и подтвердите регистрацию", None
        
        # Проверяем пароль / Verify password
        if not verify_password(password, user['password_hash']):
            return False, "Неверное имя пользователя или пароль", None
        
        # Обновляем время последнего входа / Update last login time
        user['last_login'] = datetime.now().isoformat()
        save_users(users)
        
        # Возвращаем данные пользователя без пароля / Return user data without password
        user_data = {k: v for k, v in user.items() if k != 'password_hash' and k != 'verification_code'}
        
        logging.info(f"Пользователь {user['username']} успешно аутентифицирован")
        return True, "Успешная авторизация", user_data
        
    except Exception as e:
        error_msg = f"Ошибка аутентификации: {str(e)}"
        logging.error(error_msg)
        return False, error_msg, None

def authenticate_user_with_session(username: str, password: str) -> Tuple[bool, str, Optional[Dict], Optional[str]]:
    """
    Аутентифицирует пользователя и создает сессию / Authenticates user and creates session
    
    Args:
        username: Имя пользователя или email / Username or email
        password: Пароль / Password
    
    Returns:
        Tuple[bool, str, Optional[Dict], Optional[str]]: (успех, сообщение, данные пользователя, токен сессии) / (success, message, user_data, session_token)
    """
    try:
        # Аутентифицируем пользователя / Authenticate user
        success, message, user_data = authenticate_user(username, password)
        
        if not success:
            return False, message, None, None
        
        # Импортируем функции сессий / Import session functions
        from modules.auth_middleware import create_user_session
        
        # Создаем сессию / Create session
        session_token, session_data = create_user_session(
            user_data['id'],
            user_data['username'],
            user_data['email']
        )
        
        if not session_token:
            return False, "Ошибка создания сессии", None, None
        
        logging.info(f"Создана сессия для пользователя {user_data['username']}")
        return True, message, user_data, session_token
        
    except Exception as e:
        error_msg = f"Ошибка аутентификации с сессией: {str(e)}"
        logging.error(error_msg)
        return False, error_msg, None, None

def resend_verification_code(email: str) -> Tuple[bool, str]:
    """
    Повторно отправляет код верификации / Resends verification code
    
    Args:
        email: Email пользователя / User's email
    
    Returns:
        Tuple[bool, str]: (успех, сообщение) / (success, message)
    """
    try:
        users = load_users()
        
        # Ищем пользователя / Find user
        user = None
        user_index = -1
        for i, u in enumerate(users):
            if u['email'].lower() == email.lower():
                user = u
                user_index = i
                break
        
        if not user:
            return False, "Пользователь с таким email не найден"
        
        # Проверяем статус верификации / Check verification status
        if user['verified']:
            return False, "Email уже подтвержден"
        
        # Генерируем новый код / Generate new code
        new_verification_code = generate_verification_code()
        current_time = datetime.now().isoformat()
        
        # Обновляем данные пользователя / Update user data
        users[user_index]['verification_code'] = new_verification_code
        users[user_index]['verification_attempts'] = 0
        users[user_index]['created_at'] = current_time
        
        if not save_users(users):
            return False, "Ошибка сохранения данных"
        
        # Отправляем новый код / Send new code
        email_success, email_message = send_verification_email(email, user['username'], new_verification_code)
        
        if not email_success:
            return False, f"Ошибка отправки email: {email_message}"
        
        logging.info(f"Новый код верификации отправлен на {email}")
        return True, "Новый код верификации отправлен на ваш email"
        
    except Exception as e:
        error_msg = f"Ошибка повторной отправки кода: {str(e)}"
        logging.error(error_msg)
        return False, error_msg

def get_user_by_email(email: str) -> Optional[Dict]:
    """Получает пользователя по email / Gets user by email"""
    users = load_users()
    for user in users:
        if user['email'].lower() == email.lower():
            return {k: v for k, v in user.items() if k != 'password_hash' and k != 'verification_code'}
    return None

def get_user_by_username(username: str) -> Optional[Dict]:
    """Получает пользователя по имени / Gets user by username"""
    users = load_users()
    for user in users:
        if user['username'].lower() == username.lower():
            return {k: v for k, v in user.items() if k != 'password_hash' and k != 'verification_code'}
    return None
