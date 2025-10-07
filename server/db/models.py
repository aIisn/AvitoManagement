"""
Database models for Avito Management system
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, DECIMAL, JSON
from sqlalchemy.sql import func
from .config import Base


class User(Base):
    """Users table - система пользователей"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    client_settings = Column(JSON, default=dict)
    accounts_id = Column(JSON, default=list)  # [{"account_id": 1, "alias": "Мой магазин", "is_owner": true}]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    favorite_templates = Column(JSON, default=list)  # избранные шаблоны описания


class AvitoAccount(Base):
    """Avito accounts table - аккаунты Avito"""
    __tablename__ = "avito_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(100), unique=True, nullable=False, index=True)
    client_secret = Column(String(255), unique=True, nullable=False)
    account_name = Column(String(200), nullable=False)
    phone_number = Column(String(20))
    email = Column(String(100))
    path = Column(String(255), nullable=False)  # путь к директории аккаунта
    last_check = Column(DateTime(timezone=True))
    balance = Column(DECIMAL(10, 2), default=0)
    bonuses = Column(DECIMAL(10, 2), default=0)
    advance = Column(DECIMAL(10, 2), default=0)
    count_reviews = Column(Integer, default=0)
    total_stars = Column(DECIMAL(3, 2), default=0)
    tariff_plan = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AdCard(Base):
    """Ad cards table - карточки объявлений"""
    __tablename__ = "ad_cards"
    
    id = Column(Integer, primary_key=True, index=True)
    card_name = Column(String(200), nullable=False)
    account_id = Column(Integer, nullable=False, index=True)  # связь с avito_accounts
    created_by_user_id = Column(Integer, nullable=False, index=True)  # кто создал
    links_to_file = Column(String(500))  # путь к папке с фото
    category = Column(JSON, nullable=False)  # {"main": "Одежда", "sub": "Мужская одежда"}
    images = Column(JSON, default=list)  # массив готовых ссылок на изображения
    title_phrases = Column(JSON, default=list)  # массив фраз для заголовка
    description = Column(Text)
    price_from = Column(DECIMAL(10, 2))
    price_to = Column(DECIMAL(10, 2))
    price_step = Column(DECIMAL(10, 2))
    cities = Column(JSON, default=list)  # массив городов
    others = Column(JSON, default=dict)  # остальные поля Avito
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
