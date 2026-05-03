---
task: post-release-hotfix-001
type: quick
status: done
completed: 2026-05-03
tests: 58 passed
---

# Hotfix: URL date params + double message

## Bugs

1. **URL date mismatch**: `run_check()` использовал захардкоженные `data=` и `d2=` из `BG_MONITOR_URL`. Когда админ менял даты через Telegram, фильтр ждал новые даты, а URL слал старые → 0 офферов.

2. **Двойной ответ**: `run_manual_check()` слал «Проверяю цены...» + отчёт — два сообщения на каждое нажатие кнопки.

## Fixes

### 1. URL date rewriting (`price_monitor/monitor.py:830`)

```python
# Rewrite date parameters in Biblio-Globus URLs to match current config
fetch_url = target.url
if is_bgoperator_url(target.url):
    fetch_url = re.sub(r"data=[^&]*", f"data={active_config.departure_from}", fetch_url)
    fetch_url = re.sub(r"d2=[^&]*", f"d2={active_config.departure_to}", fetch_url)
```

### 2. Remove intermediate message (`price_monitor/monitor.py:1067`)

Убран `self.send_message(chat_id, "Проверяю цены...")` из `run_manual_check`.

## Verification

- 58 тестов проходят
- URL rewrite проверен в контейнере: `data=14.10.2026&d2=17.10.2026`
- Двойное сообщение устранено

## Примечание

0 офферов на октябрь 2026 — не баг, а ограничение туроператора (5+ месяцев вперёд). Используй даты в пределах 3-4 месяцев.
