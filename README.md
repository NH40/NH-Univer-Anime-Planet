# Universe Anime Planet — Telegram-бот

Коллекционная гача-игра по аниме-вселенным в Telegram. Полный бэклог — в [TODO.md](TODO.md),
инженерные правила проекта — в [CLAUDE.md](CLAUDE.md).

## Стек

Python 3.12 · aiogram 3 · PostgreSQL (SQLAlchemy 2 async + Alembic) · Redis · FastAPI (Mini App
API) · Vite/Preact/TS (Mini App фронтенд) · Caddy (HTTPS) · Docker Compose

## Быстрый старт (бот)

1. Скопировать `.env.example` → `.env` и заполнить: `BOT_TOKEN`, `ADMIN_IDS` (через запятую,
   Telegram user id), `POSTGRES_PASSWORD`, при желании `YOOKASSA_PROVIDER_TOKEN` (это
   `provider_token` из BotFather → Bot Settings → Payments → ЮKassa, НЕ shop_id/secret_key
   с сайта ЮKassa напрямую — см. CLAUDE.md, "Донат"). `DOMAIN`/`MINI_APP_URL` пока можно
   оставить пустыми — они нужны только для Mini App, см. ниже.
2. Поднять инфраструктуру и собрать бота (без Mini App — самодостаточно):

   ```
   docker compose up -d postgres redis bot
   ```

3. Первая миграция (если папка `migrations/versions` пуста):

   ```
   docker compose run --rm bot alembic revision --autogenerate -m "init"
   docker compose run --rm bot alembic upgrade head
   ```

   В дальнейшем при изменении моделей — так же: `alembic revision --autogenerate -m "..."`,
   затем `alembic upgrade head` (или через `docker compose exec bot ...`, пока контейнер уже
   поднят).

4. Разложить карточки в `assets/cards/<universe>/<ubp>UBP/<id>_<Name>.<ext>`, например:

   ```
   assets/cards/lookism/6000UBP/001_DanielEos.png
   ```

   Существующие папки-вселенные: `assets/cards/onepiece`, `assets/cards/lookism`,
   `assets/cards/genshin`. Новую вселенную — просто новой папкой, скрипт её подхватит.

5. Загрузить карточки в БД (безопасно перезапускать при добавлении новых файлов):

   ```
   docker compose exec bot python scripts/seed_cards.py
   ```

6. Логи бота: `docker compose logs -f bot`.

## Mini App (просмотр коллекции, read-only)

Требует **реальный домен**, указывающий A-записью на этот сервер — Telegram Mini App не
откроется без валидного HTTPS, а Caddy выпускает Let's Encrypt сертификат по домену, не по IP.
Без домена весь остальной бот полностью работоспособен — просто не поднимайте `api`/`caddy`.

1. Когда домен готов и указывает на сервер — вписать его в `.env`:

   ```
   DOMAIN=example.com
   MINI_APP_URL=https://example.com
   ```

2. Поднять оставшиеся сервисы:

   ```
   docker compose up -d --build api caddy
   ```

   `caddy` при первом старте сам получит сертификат (нужны открытые 80/443 порты снаружи).

3. В BotFather: Bot Settings → Menu Button → указать `https://example.com` (или добавить
   Web App-кнопку) — тогда Mini App можно будет открыть и из системного меню Telegram, не
   только с кнопки "🖼 Коллекция (веб)" в главном меню бота (та появляется автоматически,
   как только `MINI_APP_URL` не пусто).

4. Пересоздать `bot`, чтобы подхватить `MINI_APP_URL`: `docker compose up -d bot`.

Локальная разработка фронтенда без Docker: `cd src/web && npm install && npm run dev` (Vite
проксирует `/api` на `http://localhost:8000` — поднимите `api` отдельно: `docker compose up -d
postgres api` или `uvicorn api.main:app --reload` с локальным `DATABASE_URL`).

## Структура

```
src/bot/            Telegram-бот (aiogram 3)
  main.py             точка входа, фоновый таск уведомлений
  config/             настройки (.env) и игровой баланс
  constant/           строковые константы (callback_data, ключи локов, reason'ы)
  db/                 SQLAlchemy-модели, сессии, репозитории (по доменам)
  cache/              Redis: клиент, ключи, антидубликат-локи, лидерборд
  middlewares/        db-сессия, техрежим, бан-чек (+ трекинг активности)
  services/           бизнес-логика (по доменам)
  handlers/           хендлеры команд/колбэков (по доменам)
  keyboards/ texts/    клавиатуры и тексты (по доменам)
  filters/            кастомные aiogram-фильтры (проверка админки)
src/api/            FastAPI — read-only Mini App API, initData-авторизация
src/web/            Vite + Preact + TypeScript — фронтенд Mini App
scripts/seed_cards.py  загрузка карточек из assets/cards в БД
migrations/            Alembic-миграции
assets/cards/           датасеты карточек (по вселенным)
Caddyfile / Dockerfile.web   HTTPS-прокси + статика Mini App
```

## Текущий статус

Реализованы Этапы 0–12 из TODO.md (бот целиком: профиль, гача/колода, магазин, кланы,
сезонный пасс, донат, подписка, админ-панель, Mini App) — детали и обоснования решений
по каждому этапу см. в TODO.md/CLAUDE.md. Остался Этап 13 (нагрузочная готовность:
`EXPLAIN ANALYZE` на горячих запросах, юнит-тесты, проверка идемпотентности).
