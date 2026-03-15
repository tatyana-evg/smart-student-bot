"""
Все клавиатуры бота.
"""
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from config import SUBJECTS_BY_GRADE, DIFFICULTY_LABELS


def kb_role() -> InlineKeyboardMarkup:
    """Выбор роли: ученик / родитель."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎒 Я ученик", callback_data="role:student")
    builder.button(text="👨‍👩‍👧 Я родитель", callback_data="role:parent")
    builder.adjust(1)
    return builder.as_markup()


def kb_grade_group() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🌟 2–4 класс", callback_data="grp:2-4")
    builder.button(text="📚 5–8 класс", callback_data="grp:5-8")
    builder.button(text="🎓 9–11 класс", callback_data="grp:9-11")
    builder.adjust(1)
    return builder.as_markup()


def kb_exact_grade(group: str) -> InlineKeyboardMarkup:
    """Выбор конкретного класса."""
    builder = InlineKeyboardBuilder()
    ranges = {"2-4": range(2, 5), "5-8": range(5, 9), "9-11": range(9, 12)}
    for g in ranges.get(group, []):
        builder.button(text=f"{g} класс", callback_data=f"grade:{g}")
    builder.adjust(3)
    return builder.as_markup()


def kb_subjects(grade_group: str) -> InlineKeyboardMarkup:
    """Список предметов по группе классов."""
    builder = InlineKeyboardBuilder()
    subjects = SUBJECTS_BY_GRADE.get(grade_group, [])
    for subj in subjects:
        builder.button(text=subj, callback_data=f"subj:{subj}")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()


def kb_difficulty() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, label in DIFFICULTY_LABELS.items():
        builder.button(text=label, callback_data=f"diff:{key}")
    builder.adjust(1)
    return builder.as_markup()


def kb_after_task(correct: bool) -> InlineKeyboardMarkup:
    """Кнопки после проверки ответа."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ Следующее задание", callback_data="task:next")
    if not correct:
        builder.button(text="💡 Подсказка", callback_data="task:hint")
    builder.button(text="🔀 Сменить предмет", callback_data="task:change_subject")
    builder.button(text="📊 Мой прогресс", callback_data="profile:show")
    builder.adjust(1)
    return builder.as_markup()


def kb_main_student() -> InlineKeyboardMarkup:
    """Главное меню ученика."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Начать задание", callback_data="task:start")
    builder.button(text="🏆 Мой рейтинг", callback_data="profile:show")
    builder.button(text="🎁 Магазин наград", callback_data="profile:rewards")
    builder.button(text="📊 Прогресс", callback_data="profile:stats")
    builder.adjust(2)
    return builder.as_markup()


def kb_main_parent() -> InlineKeyboardMarkup:
    """Главное меню родителя."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Прогресс ребёнка", callback_data="parent:stats")
    builder.button(text="🔗 Привязать аккаунт", callback_data="parent:link")
    builder.button(text="⚙️ Настройки", callback_data="parent:settings")
    builder.adjust(1)
    return builder.as_markup()


def kb_confirm_answer() -> InlineKeyboardMarkup:
    """Подтверждение при вводе задачи (текстовой)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить ответ", callback_data="task:submit")
    builder.button(text="💡 Нужна подсказка", callback_data="task:hint")
    builder.button(text="⏭️ Пропустить", callback_data="task:skip")
    builder.adjust(2)
    return builder.as_markup()


def kb_back_to_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 В главное меню", callback_data="main_menu")
    return builder.as_markup()
