version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: smart_student
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  bot:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      BOT_TOKEN: ${BOT_TOKEN}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      DATABASE_URL: postgresql+asyncpg://postgres:password@postgres:5432/smart_student
    env_file:
      - .env
    restart: unless-stopped

volumes:
  pgdata:
