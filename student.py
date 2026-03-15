"""
Хэндлеры для режима родителя.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import async_session_factory
from database.crud import get_user, update_user_field, get_weekly_stats
from keyboards.keyboards import kb_main_parent, kb_back_to_menu
from utils.states import ParentStates

router = Router()


@router.callback_query(F.data == "parent:stats")
async def cb_parent_stats(call: CallbackQuery, state: FSMContext):
    """Показать прогресс привязанного ребёнка."""
    async with async_session_factory() as session:
        parent = await get_user(session, call.from_user.id)

    if not parent or not parent.linked_student_id:
        await call.message.edit_text(
            "🔗 <b>Аккаунт ребёнка не привязан.</b>\n\n"
            "Нажми «Привязать аккаунт» и попроси ребёнка прислать тебе его ID.",
            reply_markup=kb_main_parent()
        )
        await call.answer()
        return

    async with async_session_factory() as session:
        stats = await get_weekly_stats(session, parent.linked_student_id)

    if not stats:
        await call.answer("Ребёнок ещё не начал занятия.", show_alert=True)
        return

    subjects_text = ""
    for subj, cnt in stats.get("subjects", {}).items():
        subjects_text += f"  • {subj}: {cnt} задание(й)\n"

    text = (
        f"📊 <b>Отчёт за неделю</b>\n\n"
        f"👦 <b>{stats['name']}</b> на этой неделе:\n"
        f"✅ Решил задач: <b>{stats['total_tasks']}</b>\n"
        f"💰 Заработал баллов: <b>{stats['points']}</b>\n\n"
        f"<b>По предметам:</b>\n{subjects_text or '  Нет данных\n'}\n"
        f"📈 Всего баллов: <b>{stats['total_points']}</b>  |  {stats['rank']}"
    )

    # Мотивационная вставка для родителя
    next_reward_pts = None
    from config import REWARD_THRESHOLDS
    for threshold in sorted(REWARD_THRESHOLDS.keys()):
        if stats["total_points"] < threshold:
            next_reward_pts = threshold - stats["total_points"]
            r = REWARD_THRESHOLDS[threshold]
            text += f"\n\n🎁 До подарка «{r['title']}» осталось <b>{next_reward_pts} баллов</b>!"
            break

    await call.message.edit_text(text, reply_markup=kb_back_to_menu())
    await call.answer()


@router.callback_query(F.data == "parent:link")
async def cb_parent_link(call: CallbackQuery, state: FSMContext):
    """Инструкция по привязке аккаунта ребёнка."""
    await state.set_state(ParentStates.entering_child_id)
    await call.message.edit_text(
        "🔗 <b>Привязка аккаунта ребёнка</b>\n\n"
        "1. Попроси ребёнка открыть бот и нажать /myid\n"
        "2. Ребёнок получит свой ID\n"
        "3. Введи этот ID ниже:\n\n"
        "<i>Пример: 123456789</i>"
    )
    await call.answer()


@router.message(ParentStates.entering_child_id)
async def handle_child_id(message: Message, state: FSMContext):
    """Привязка ребёнка по Telegram ID."""
    try:
        child_telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи только число (ID ребёнка).")
        return

    async with async_session_factory() as session:
        child = await get_user(session, child_telegram_id)

    if not child:
        await message.answer(
            "❌ Ученик с таким ID не найден. Убедись, что ребёнок уже запустил бота."
        )
        return

    if child.role != "student":
        await message.answer("❌ Этот аккаунт не является аккаунтом ученика.")
        return

    async with async_session_factory() as session:
        await update_user_field(session, message.from_user.id,
                                 linked_student_id=child_telegram_id)
        await update_user_field(session, child_telegram_id,
                                 linked_parent_id=message.from_user.id)

    await state.set_state(ParentStates.main_menu)
    await message.answer(
        f"✅ Аккаунт <b>{child.first_name}</b> успешно привязан!\n\n"
        f"Теперь вы будете получать еженедельные отчёты об успехах ребёнка.",
        reply_markup=kb_main_parent()
    )


@router.message(F.text == "/myid")
async def cmd_my_id(message: Message):
    """Показать свой Telegram ID (для привязки к родителю)."""
    await message.answer(
        f"🆔 Твой ID: <code>{message.from_user.id}</code>\n\n"
        "Отправь это число родителю — он введёт его в боте для привязки аккаунтов."
    )


@router.callback_query(F.data == "parent:settings")
async def cb_parent_settings(call: CallbackQuery, state: FSMContext):
    """Настройки родительского контроля (заглушка)."""
    await call.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "🔔 Еженедельные отчёты: <b>включены</b>\n"
        "📅 День отчёта: <b>воскресенье</b>\n\n"
        "<i>Расширенные настройки будут доступны в следующей версии.</i>",
        reply_markup=kb_back_to_menu()
    )
    await call.answer()
