"""
CRUD-операции с базой данных.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import User, StudySession, UserReward, WeeklyStats
from config import RANKS, REWARD_THRESHOLDS


async def get_or_create_user(session: AsyncSession, telegram_id: int,
                              username: str = None, first_name: str = None) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name or "Ученик",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def update_user_field(session: AsyncSession, telegram_id: int, **kwargs):
    await session.execute(
        update(User).where(User.telegram_id == telegram_id).values(**kwargs)
    )
    await session.commit()


async def get_user(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def add_session(session: AsyncSession, user: User, subject: str,
                       difficulty: str, task_text: str) -> StudySession:
    study = StudySession(
        user_id=user.id,
        subject=subject,
        grade=user.grade,
        difficulty=difficulty,
        task_text=task_text,
    )
    session.add(study)
    await session.commit()
    await session.refresh(study)
    return study


async def update_session_answer(session: AsyncSession, study_id: int,
                                  answer: str, is_correct: bool, points: int):
    await session.execute(
        update(StudySession)
        .where(StudySession.id == study_id)
        .values(user_answer=answer, is_correct=is_correct,
                points_earned=points, attempts=StudySession.attempts + 1)
    )
    await session.commit()


def get_rank(points: int) -> str:
    rank = RANKS[0][1]
    for threshold, label in RANKS:
        if points >= threshold:
            rank = label
    return rank


async def add_points(session: AsyncSession, telegram_id: int,
                      points: int, correct: bool) -> tuple[int, list[dict]]:
    """Добавить баллы, обновить стрик и ранг. Возвращает (новые_баллы, новые_награды)."""
    user = await get_user(session, telegram_id)
    if not user:
        return 0, []

    new_streak = (user.streak + 1) if correct else 0
    multiplier = 1.5 if new_streak >= 3 else 1.0
    actual_points = int(points * multiplier)

    new_total = user.total_points + actual_points
    new_rank = get_rank(new_total)
    max_streak = max(user.max_streak, new_streak)

    await session.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(
            total_points=new_total,
            streak=new_streak,
            max_streak=max_streak,
            rank=new_rank,
            last_active=datetime.utcnow()
        )
    )

    # Проверка достижения порогов
    new_rewards = []
    for threshold, reward_data in REWARD_THRESHOLDS.items():
        if user.total_points < threshold <= new_total:
            # Проверяем, не выдавали ли уже
            existing = await session.execute(
                select(UserReward).where(
                    UserReward.user_id == user.id,
                    UserReward.threshold == threshold
                )
            )
            if not existing.scalar_one_or_none():
                reward = UserReward(
                    user_id=user.id,
                    threshold=threshold,
                    reward_title=reward_data["title"],
                    promo_code=reward_data["promo"],
                )
                session.add(reward)
                new_rewards.append(reward_data)

    await session.commit()
    return new_total, new_rewards


async def get_weekly_stats(session: AsyncSession, student_telegram_id: int) -> dict:
    """Статистика за последние 7 дней для родительского отчёта."""
    week_ago = datetime.utcnow() - timedelta(days=7)
    user = await get_user(session, student_telegram_id)
    if not user:
        return {}

    result = await session.execute(
        select(
            func.count(StudySession.id).label("total"),
            func.sum(StudySession.points_earned).label("points"),
        )
        .where(
            StudySession.user_id == user.id,
            StudySession.created_at >= week_ago
        )
    )
    row = result.one()

    # Предметы
    subj_result = await session.execute(
        select(StudySession.subject, func.count(StudySession.id).label("cnt"))
        .where(StudySession.user_id == user.id, StudySession.created_at >= week_ago)
        .group_by(StudySession.subject)
    )
    subjects = {r.subject: r.cnt for r in subj_result}

    return {
        "name": user.first_name,
        "total_tasks": row.total or 0,
        "points": row.points or 0,
        "subjects": subjects,
        "total_points": user.total_points,
        "rank": user.rank,
    }
