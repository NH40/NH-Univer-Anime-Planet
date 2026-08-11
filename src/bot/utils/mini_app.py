from __future__ import annotations

# Версия статики Mini App — бампить вручную при каждом деплое фронтенда. Telegram кэширует
# Mini App URL агрессивнее, чем можно управлять серверными заголовками Cache-Control (см.
# CLAUDE.md, "Долгая загрузка картинок..." — там же баг, из-за которого это завели): один
# и тот же URL после редеплоя мог продолжать открывать СТАРЫЙ index.html/JS, закэшированный
# клиентом ДО того, как на Caddy появился no-cache. Приклеенный ?v=N делает URL кнопки
# формально НОВЫМ при каждом бампе — Telegram не может отдать под него старый кэш, которого
# для этого URL ещё не существовало.
MINI_APP_ASSET_VERSION = 2


def mini_app_url(base_url: str, *, view: str | None = None) -> str:
    params = [f"v={MINI_APP_ASSET_VERSION}"]
    if view:
        params.append(f"view={view}")
    return f"{base_url}?{'&'.join(params)}"
