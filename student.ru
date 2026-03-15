from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from database.db import async_session_factory
from database.crud import get_user
from keyboards.keyboards import kb_main_student
from utils.states import StudentStates

router = Router()

@router.callback_query(F.data == "student:menu")
async def cb_student_menu(call: CallbackQuery, state: FSMContext):
    async with async_session_factory() as session:
        user = await get_user(session, call.from_user.id)
    name = call.from_user.first_name or "Ученик"
    points = user.total_points if user else 0
    rank = user.rank if user else "🌱 Новичок"
    await state.set_state(StudentStates.main_menu)
    await call.message.edit_text(
        f"🎒 <b>Привет, {name}!</b>\n\n"
        f"🏆 Баллы: <b>{points}</b>  |  Ранг: {rank}\n\n"
        "Выбери, чем займёмся:",
        reply_markup=kb_main_student()
    )
    await call.answer()
