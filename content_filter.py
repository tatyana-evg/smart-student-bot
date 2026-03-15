"""
Состояния конечного автомата (FSM) для управления диалогом.
"""
from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    choosing_role = State()
    choosing_grade_group = State()
    choosing_exact_grade = State()
    entering_name = State()


class StudentStates(StatesGroup):
    main_menu = State()
    choosing_subject = State()
    choosing_difficulty = State()
    solving_task = State()          # Ученик решает задание
    waiting_for_answer = State()    # Ожидание текстового ответа
    viewing_profile = State()


class ParentStates(StatesGroup):
    main_menu = State()
    entering_child_id = State()     # Привязка аккаунта ребёнка
    viewing_stats = State()
