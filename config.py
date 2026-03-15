import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/smart_student"
)

REWARD_THRESHOLDS = {
    500: {"title": "📚 Книга в ЛитРес", "description": "Промокод на бесплатную книгу!", "promo": "LITRES-SMART-500"},
    1000: {"title": "🎓 Курс на Stepik", "description": "Скидка 20% на курс!", "promo": "STEPIK-SMART-1000"},
    2500: {"title": "🎨 Нейросеть-художник", "description": "Доступ к генерации арта!", "promo": "ART-SMART-2500"},
}

RANKS = [
    (0, "🌱 Новичок"),
    (101, "📖 Знаток"),
    (501, "🧠 Эрудит"),
    (1001, "🎓 Профессор"),
]

SUBJECTS_BY_GRADE = {
    "2-4": ["📐 Математика", "📝 Русский язык", "🌍 Окружающий мир", "📖 Чтение"],
    "5-8": ["📐 Математика", "📝 Русский язык", "🇬🇧 Английский язык", "⚗️ Физика", "🔬 Биология", "📜 История", "🌐 География"],
    "9-11": ["📐 Математика", "📝 Русский язык", "🇬🇧 Английский язык", "⚗️ Физика", "🧪 Химия", "💻 Информатика", "📜 История", "🔬 Биология", "🌐 География"],
}

DIFFICULTY_LABELS = {
    "easy": "😊 Лёгкий",
    "medium": "🔥 Средний",
    "hard": "⭐ Сложный (со звёздочкой)",
}
