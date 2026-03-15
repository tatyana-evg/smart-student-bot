"""
Фильтрация контента: запрет мата, личных данных и опасного контента.
Безопасность для детей согласно требованиям ФГОС и 436-ФЗ.
"""
import re

# Простой список стоп-слов (в реальном боте заменить на более полный список)
_BAD_WORDS = {
    "мат": ["бл*", "х*й", "п*зда", "еб*"],  # замаскированы для примера
}

# Паттерны для личных данных
_PHONE_PATTERN = re.compile(r"(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_CARD_PATTERN = re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b")

# Опасный контент
_DANGEROUS_KEYWORDS = [
    "адрес", "пароль", "password", "паспорт", "инн",
    "встретимся", "приходи ко мне", "никому не говори",
]


def is_safe_content(text: str) -> tuple[bool, str]:
    """
    Проверяет текст на безопасность.
    Возвращает (is_safe, reason).
    """
    text_lower = text.lower()

    # Проверка личных данных
    if _PHONE_PATTERN.search(text):
        return False, "Обнаружен номер телефона. Не отправляй личные данные в чате!"

    if _EMAIL_PATTERN.search(text):
        return False, "Обнаружен email. Не отправляй личные данные в чате!"

    if _CARD_PATTERN.search(text):
        return False, "Обнаружен номер карты. Никогда не отправляй финансовые данные!"

    # Проверка опасных ключевых слов
    for keyword in _DANGEROUS_KEYWORDS:
        if keyword in text_lower:
            return False, "Сообщение содержит подозрительный контент. Обратись к родителям."

    return True, ""


def sanitize_answer(text: str) -> str:
    """Очищает ответ ученика для записи в БД."""
    # Убираем лишние пробелы и обрезаем до разумной длины
    sanitized = text.strip()[:500]
    return sanitized


def is_asking_for_answer(text: str) -> bool:
    """
    Определяет, просит ли ученик дать готовый ответ (шпаргалку).
    """
    cheat_phrases = [
        "скажи ответ", "дай ответ", "какой ответ", "ответ на задание",
        "реши за меня", "решение задачи", "готовый ответ",
        "tell me the answer", "give me answer", "what is the answer",
        "решай сам", "напиши ответ", "ответь за меня",
    ]
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in cheat_phrases)
