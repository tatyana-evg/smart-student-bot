"""
Хэндлеры учебных заданий — основная логика обучения.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import async_session_factory
from database.crud import get_user, add_session, update_session_answer, add_points
from keyboards.keyboards import (
    kb_subjects, kb_difficulty, kb_after_task, kb_main_student, kb_back_to_menu
)
from utils.states import StudentStates
from utils.ai_engine import generate_task, check_answer, get_encouragement
from utils.content_filter import is_safe_content, sanitize_answer, is_asking_for_answer
from config import REWARD_THRESHOLDS

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "task:start")
async def cb_task_start(call: CallbackQuery, state: FSMContext):
    """Начало выбора задания — выбор предмета."""
    async with async_session_factory() as session:
        user = await get_user(session, call.from_user.id)

    if not user or not user.grade_group:
        await call.answer("Сначала выбери класс!", show_alert=True)
        return

    await state.set_state(StudentStates.choosing_subject)
    await call.message.edit_text(
        "📚 <b>Выбери предмет</b>\n\nПо какому предмету займёмся сегодня?",
        reply_markup=kb_subjects(user.grade_group)
    )
    await call.answer()


@router.callback_query(F.data.startswith("subj:"))
async def cb_subject(call: CallbackQuery, state: FSMContext):
    """Выбор предмета."""
    subject = call.data.split("subj:")[1]
    await state.update_data(subject=subject)
    await state.set_state(StudentStates.choosing_difficulty)

    await call.message.edit_text(
        f"✅ Предмет: <b>{subject}</b>\n\nВыбери уровень сложности:",
        reply_markup=kb_difficulty()
    )
    await call.answer()


@router.callback_query(F.data.startswith("diff:"))
async def cb_difficulty(call: CallbackQuery, state: FSMContext):
    """Выбор сложности и генерация задания."""
    difficulty = call.data.split(":")[1]
    await state.update_data(difficulty=difficulty)

    data = await state.get_data()
    subject = data.get("subject", "📐 Математика")

    async with async_session_factory() as session:
        user = await get_user(session, call.from_user.id)
        grade = user.grade if user else "5"

    await call.message.edit_text("⏳ Генерирую задание для тебя...")
    await _send_new_task(call, state, subject, difficulty, grade)
    await call.answer()


async def _send_new_task(call: CallbackQuery, state: FSMContext,
                          subject: str, difficulty: str, grade: str):
    """Генерация и отправка нового задания."""
    task_data = await generate_task(subject, grade, difficulty)

    # Сохраняем задание в БД
    async with async_session_factory() as session:
        user = await get_user(session, call.from_user.id)
        if user:
            study = await add_session(session, user, subject, difficulty, task_data["task"])
            await state.update_data(
                study_id=study.id,
                task_data=task_data,
                subject=subject,
                difficulty=difficulty,
                attempt=0
            )

    await state.set_state(StudentStates.waiting_for_answer)

    difficulty_emoji = {"easy": "😊", "medium": "🔥", "hard": "⭐"}.get(difficulty, "📝")
    topic = task_data.get("topic", "")

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="💡 Подсказка", callback_data="task:hint")
    builder.button(text="⏭️ Пропустить", callback_data="task:skip")
    builder.adjust(2)

    await call.message.edit_text(
        f"{difficulty_emoji} <b>Задание</b> | {subject}\n"
        f"📌 Тема: <i>{topic}</i>\n\n"
        f"<b>{task_data['task']}</b>\n\n"
        f"✏️ <i>Напиши свой ответ:</i>",
        reply_markup=builder.as_markup()
    )


@router.message(StudentStates.waiting_for_answer)
async def handle_answer(message: Message, state: FSMContext):
    """Обработка ответа ученика."""
    user_text = message.text or ""

    # Проверка безопасности контента
    safe, reason = is_safe_content(user_text)
    if not safe:
        await message.answer(f"⚠️ {reason}")
        return

    # Ученик просит готовый ответ — играем роль учителя
    if is_asking_for_answer(user_text):
        await message.answer(
            "😄 Я учитель, а не шпаргалка!\n\n"
            "Давай подумаем <b>вместе</b>. С чего бы ты начал решать?\n"
            "Нажми 💡 <b>Подсказка</b>, если нужна помощь!",
        )
        return

    data = await state.get_data()
    task_data = data.get("task_data", {})
    study_id = data.get("study_id")
    attempt = data.get("attempt", 0)

    if not task_data:
        await message.answer("Что-то пошло не так. Нажми /start для перезапуска.")
        return

    async with async_session_factory() as session:
        user = await get_user(session, message.from_user.id)
        grade = user.grade if user else "5"
        subject = user.current_subject or data.get("subject", "")

    # Проверяем ответ через AI
    check = await check_answer(
        task=task_data["task"],
        correct_answer=task_data["correct_answer"],
        user_answer=sanitize_answer(user_text),
        grade=grade,
        subject=subject,
    )

    is_correct = check.get("is_correct", False)
    feedback = check.get("feedback", "")
    spelling_note = check.get("spelling_note")

    if is_correct:
        # Начисляем баллы (с учётом стрика)
        points_for_task = {"easy": 10, "medium": 15, "hard": 25}.get(
            data.get("difficulty", "easy"), 10
        )
        async with async_session_factory() as session:
            new_total, new_rewards = await add_points(session, message.from_user.id,
                                                       points_for_task, True)
            user = await get_user(session, message.from_user.id)
            streak = user.streak if user else 1

        if study_id:
            async with async_session_factory() as session:
                await update_session_answer(session, study_id, user_text, True, points_for_task)

        # Формируем ответ
        streak_bonus = f"\n🔥 <b>Серия x{streak}!</b> Множитель 1.5x применён!" if streak >= 3 else ""
        spelling_text = f"\n\n📝 <i>Заметка: {spelling_note}</i>" if spelling_note else ""

        response = (
            f"✅ <b>Верно! Молодец!</b>\n\n"
            f"{feedback}\n"
            f"💰 +{points_for_task} баллов | Итого: <b>{new_total}</b>"
            f"{streak_bonus}{spelling_text}"
        )

        # Уведомления о наградах
        for reward in new_rewards:
            response += (
                f"\n\n🎁 <b>ПОЗДРАВЛЯЕМ! Новая награда!</b>\n"
                f"{reward['title']}\n{reward['description']}\n"
                f"🔑 Промокод: <code>{reward['promo']}</code>"
            )

        # Мотивация при серии
        if streak >= 3:
            encouragement = await get_encouragement(message.from_user.first_name, streak)
            response += f"\n\n{encouragement}"

        await message.answer(response, reply_markup=kb_after_task(correct=True))

    else:
        # Неверный ответ
        await state.update_data(attempt=attempt + 1)
        if study_id:
            async with async_session_factory() as session:
                await update_session_answer(session, study_id, user_text, False, 0)

        # После 2 ошибок даём объяснение
        if attempt >= 1:
            explanation = task_data.get("explanation", "")
            hint2 = task_data.get("hint2", "")
            response = (
                f"❌ <b>Не совсем.</b> {feedback}\n\n"
                f"💡 <b>Разбор:</b> {explanation}\n\n"
                f"📚 <b>Правило:</b> {hint2}\n\n"
                f"<i>Попробуй похожее задание для закрепления!</i>"
            )
        else:
            hint1 = task_data.get("hint1", "")
            response = (
                f"❌ <b>Не совсем.</b> {feedback}\n\n"
                f"🤔 {hint1}\n\n"
                f"<i>Попробуй ещё раз!</i>"
            )

        spelling_text = f"\n\n📝 <i>{spelling_note}</i>" if spelling_note else ""
        response += spelling_text

        # Обнуляем стрик
        async with async_session_factory() as session:
            await add_points(session, message.from_user.id, 0, False)

        await message.answer(response, reply_markup=kb_after_task(correct=False))


@router.callback_query(F.data == "task:hint")
async def cb_hint(call: CallbackQuery, state: FSMContext):
    """Выдача подсказки."""
    data = await state.get_data()
    task_data = data.get("task_data", {})
    attempt = data.get("attempt", 0)

    if attempt == 0:
        hint = task_data.get("hint1", "Подумай внимательно о условии задачи.")
    else:
        hint = task_data.get("hint2", "Вспомни правило по данной теме из учебника.")

    await call.message.answer(f"💡 <b>Подсказка:</b>\n\n{hint}")
    await call.answer()


@router.callback_query(F.data == "task:next")
async def cb_next_task(call: CallbackQuery, state: FSMContext):
    """Следующее задание по той же теме."""
    data = await state.get_data()
    subject = data.get("subject")
    difficulty = data.get("difficulty", "easy")

    if not subject:
        await call.message.edit_text("Выбери предмет:", reply_markup=None)
        return

    async with async_session_factory() as session:
        user = await get_user(session, call.from_user.id)
        grade = user.grade if user else "5"

    await call.message.edit_text("⏳ Генерирую следующее задание...")
    await _send_new_task(call, state, subject, difficulty, grade)
    await call.answer()


@router.callback_query(F.data == "task:skip")
async def cb_skip_task(call: CallbackQuery, state: FSMContext):
    """Пропустить задание."""
    data = await state.get_data()
    subject = data.get("subject")
    difficulty = data.get("difficulty", "easy")

    async with async_session_factory() as session:
        user = await get_user(session, call.from_user.id)
        grade = user.grade if user else "5"

    await call.message.edit_text("⏭️ Пропускаем, генерирую новое...")
    await _send_new_task(call, state, subject, difficulty, grade)
    await call.answer()


@router.callback_query(F.data == "task:change_subject")
async def cb_change_subject(call: CallbackQuery, state: FSMContext):
    """Сменить предмет."""
    async with async_session_factory() as session:
        user = await get_user(session, call.from_user.id)

    await state.set_state(StudentStates.choosing_subject)
    await call.message.edit_text(
        "📚 Выбери предмет:",
        reply_markup=kb_subjects(user.grade_group if user else "5-8")
    )
    await call.answer()
