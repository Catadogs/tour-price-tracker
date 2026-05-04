# Phase 3 (06-ghcr) — Summary

**Completed:** 2026-05-04
**Tests:** 87 pass (no app changes)

## Done

- ✅ **GHCR-01**: CI пушит Docker-образ в `ghcr.io/<owner>/bg-price-monitor:latest` и `:sha-<short>`
- ✅ **GHCR-02**: docker-compose.yml содержит закомментированный пример с готовым образом

## Changes

### `.github/workflows/ci.yml`
- Добавлен job `push`: логин в ghcr.io, сборка, теги `latest` + `sha-XXXXXXX`, пуш
- Срабатывает только при пуше в `main`
- Требует `packages: write` permission

### `docker-compose.yml`
- Добавлен комментарий-инструкция как переключиться на готовый образ из GHCR

## Как использовать GHCR

1. Закомментировать `build:` и `image: bg-price-monitor:latest` в docker-compose.yml
2. Раскомментировать `# image: ghcr.io/<your-username>/bg-price-monitor:latest`
3. `docker compose pull && docker compose up -d`
