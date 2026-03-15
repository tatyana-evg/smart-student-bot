"""
База данных: модели и инициализация (SQLAlchemy async + PostgreSQL).
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    Boolean, ForeignKey, Text, BigInteger
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

from config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class User(Base):
    """Профиль пользователя."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    role = Column(String(10), nullable=True)  # "student" | "parent"
    grade = Column(String(5), nullable=True)   # "2", "3", ..., "11"
    grade_group = Column(String(5), nullable=True)  # "2-4", "5-8", "9-11"
    current_subject = Column(String(50), nullable=True)
    current_difficulty = Column(String(10), nullable=True)
    total_points = Column(Integer, default=0)
    streak = Column(Integer, default=0)        # Текущая серия правильных ответов
    max_streak = Column(Integer, default=0)
    rank = Column(String(30), default="🌱 Новичок")
    linked_parent_id = Column(BigInteger, nullable=True)  # telegram_id родителя
    linked_student_id = Column(BigInteger, nullable=True)  # telegram_id ученика
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions = relationship("StudySession", back_populates="user", lazy="select")
    rewards = relationship("UserReward", back_populates="user", lazy="select")


class StudySession(Base):
    """История учебных сессий."""
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(50))
    grade = Column(String(5))
    difficulty = Column(String(10))
    task_text = Column(Text)
    user_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    points_earned = Column(Integer, default=0)
    attempts = Column(Integer, default=0)
    hint_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sessions")


class UserReward(Base):
    """Полученные награды."""
    __tablename__ = "user_rewards"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    threshold = Column(Integer)          # За сколько баллов получена
    reward_title = Column(String(100))
    promo_code = Column(String(50))
    issued_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="rewards")


class WeeklyStats(Base):
    """Еженедельная статистика для родителей."""
    __tablename__ = "weekly_stats"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_start = Column(DateTime)
    tasks_solved = Column(Integer, default=0)
    tasks_correct = Column(Integer, default=0)
    points_earned = Column(Integer, default=0)
    subjects_studied = Column(String(200), default="")  # JSON-строка


# ─── Движок и фабрика сессий ───────────────────────────────────────────────

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Создание всех таблиц при первом запуске."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Получить сессию БД."""
    async with async_session_factory() as session:
        yield session
