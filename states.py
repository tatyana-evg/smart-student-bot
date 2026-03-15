"""
Планировщик еженедельных отчётов для родителей.
Запускается вместе с ботом как фоновая задача.
"""
import asyncio
import logging
from datetime import datetime
from aiogram import Bot
from sqlalchemy import select

from database.db import async_session_factory, User
from database.crud import get_weekly_stats
from config import REWARD_THRESHOLDS

logger = logging.getLogger(__name__)


async def send_weekly_reports(bot: Bot):
    """Отправляет еженедельные отчёты всем родителям с привязанными детьми."""
    async with async_session_factory() as session:
        # Получаем всех родителей с привязанными детьми
        result = await session.execute(
            select(User).where(
                User.role == "parent",
                User.linked_student_id.isnot(None)
            )
        )
        parents = result.scalars().all()

    for parent in parents:
        try:
            stats = await _get_stats_for_parent(parent.linked_student_id)
            if not stats:
                continue

            report = _build_report(stats)
            await bot.send_message(parent.telegram_id, report, parse_mode="HTML")
            logger.info(f"Weekly report sent to parent {parent.telegram_id}")

        except Exception as e:
            logger.error(f"Failed to send report to {parent.telegram_id}: {e}")

        await asyncio.sleep(0.1)  # Avoid flood


async def _get_stats_for_parent(student_telegram_id: int) -> dict:
    async with async_session_factory() as session:
        return await get_weekly_stats(session, student_telegram_id)


def _build_report(stats: dict) -> str:
    """Формирует текст еженедельного отчёта."""
    name = stats.get("name", "Ваш ребёнок")
    total_tasks = stats.get("total_tasks", 0)
    points = stats.get("points", 0)
    subjects = stats.get("subjects", {})
    total_points = stats.get("total_points", 0)
    rank = stats.get("rank", "🌱 Новичок")

    if not total_tasks:
        return (
            f"📊 <b>Еженедельный отчёт</b>\n\n"
            f"<b>{name}</b> на этой неделе не занимался(-ась) в боте.\n\n"
            f"Попробуй напомнить ребёнку об учёбе! 📚"
        )

    subjects_text = ""
    for subj, cnt in subjects.items():
        subjects_text += f"  • {subj}: {cnt} задание(й)\n"

    # Поиск ближайшей награды
    reward_text = ""
    for threshold in sorted(REWARD_THRESHOLDS.keys()):
        if total_points < threshold:
            r = REWARD_THRESHOLDS[threshold]
            left = threshold - total_points
            reward_text = f"\n🎁 До подарка «{r['title']}» осталось <b>{left} баллов</b>!"
            break

    return (
        f"📊 <b>Еженедельный отчёт об успехах</b>\n\n"
        f"👦 <b>{name}</b> на этой неделе:\n"
        f"✅ Решил задач: <b>{total_tasks}</b>\n"
        f"💰 Заработал баллов: <b>{points}</b>\n\n"
        f"<b>По предметам:</b>\n{subjects_text}"
        f"\n📈 Всего баллов: <b>{total_points}</b>  |  {rank}"
        f"{reward_text}\n\n"
        f"<i>Продолжайте в том же духе! 🚀</i>"
    )


async def weekly_scheduler(bot: Bot):
    """Фоновый планировщик: каждое воскресенье в 18:00."""
    while True:
        now = datetime.now()
        # Воскресенье = 6, 18:00
        if now.weekday() == 6 and now.hour == 18 and now.minute == 0:
            logger.info("Sending weekly reports...")
            await send_weekly_reports(bot)
            await asyncio.sleep(60)  # Пропустить минуту после отправки
        await asyncio.sleep(30)
