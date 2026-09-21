#!/usr/bin/env sh
# Тот же удобный паттерн, что в NH-BTFChat (и теперь в соседнем NH-Lookism-Bot):
# `docker compose up -d --build` — единственная команда, которая нужна для деплоя.
# Миграции применяются автоматически при старте контейнера бота, руками
# `docker compose exec bot alembic upgrade head` гонять не нужно.
#
# Этот образ используется несколькими сервисами с разными командами запуска (bot и
# api, см. docker-compose.yml — тот же shared image, что описан в CLAUDE.md, "Mini App").
# Если аргументы переданы (api запускается через `command: uvicorn api.main:app ...`),
# выполняем их как есть, без миграций (api read-only, ничего не мигрирует). Без
# аргументов (обычный запуск bot) — сперва миграции, потом сам бот.
set -e

if [ "$#" -eq 0 ]; then
    python -m alembic upgrade head
    exec python -m bot.main
else
    exec "$@"
fi
