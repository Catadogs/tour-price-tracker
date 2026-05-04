# Phase 1: Cross-Provider Comparison — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Фаза 1 добавляет сравнение цен одного отеля между Biblio-Globus, Level.Travel и Travelata. Когда администратор добавляет поиски одного отеля на разных сайтах, бот группирует их по названию (fuzzy matching) и показывает единый блок сравнения в Telegram-отчёте.

**Как это работает сейчас:**
- BG-поиски: парсятся в структурированные `Offer` (дата, ночи, комната, цена), форматируются через `format_report()`
- Внешние поиски: парсятся в `ExternalPrice` (отель, мин. цена), форматируются через `format_external_report()`
- Отчёты идут друг за другом, без связи между провайдерами

**Что изменится:**
- После обработки всех поисков, бот группирует результаты по отелю (fuzzy match названий)
- Если отель найден у 2+ провайдеров, добавляется блок `🌐 *Сравнение цен*`

</domain>

<decisions>
## Implementation Decisions

### Fuzzy matching (CMP-01)
- **D-01:** Использовать `difflib.SequenceMatcher` из стандартной библиотеки — без новых зависимостей.
- **D-02:** Порог схожести: 0.6 (ratio). Названия в нижнем регистре, без спецсимволов.
- **D-03:** Матчинг только по названию отеля. Даты и ночи не матчатся (у внешних провайдеров нет такой детализации).
- **D-04:** Функция `match_hotels_across_providers(results: list[TargetResult]) -> list[HotelGroup]` группирует результаты.

### Comparison report (CMP-02)
- **D-05:** Новый блок в отчёте после всех индивидуальных отчётов.
- **D-06:** Формат блока:
  ```
  🌐 *Сравнение цен*
  🏩 Отель: InterContinental
    Библио-Глобус: от 280 000 RUB (14.09, 12н)
    Level.Travel: от 305 000 RUB
    Travelata: от 295 000 RUB
  ```
- **D-07:** Для BG показывается лучшая цена с датой и ночами. Для внешних — мин. цена со страницы.
- **D-08:** Отели только с одним провайдером не попадают в сравнение.
- **D-09:** Если нет пересечений — блок не показывается.

### Data structure
- **D-10:** Новый датакласс `TargetResult` — результат парсинга одного поиска:
  ```python
  @dataclass(frozen=True)
  class TargetResult:
      target_name: str
      provider: str
      hotel_name: str | None
      best_by_date: dict[str, dict[int, Offer]] | None
      external_price: ExternalPrice | None
  ```
- **D-11:** Новый датакласс `HotelGroup` — группа результатов для одного отеля:
  ```python
  @dataclass(frozen=True)
  class HotelGroup:
      hotel_name: str
      results: list[TargetResult]
  ```

### Integration
- **D-12:** `run_check()` возвращает и отчёт, и список `TargetResult` для внешней обработки.
- **D-13:** Функция `format_comparison(groups: list[HotelGroup]) -> str | None` форматирует блок сравнения.

</decisions>

<requirements>
## Requirements Covered

- [ ] **CMP-01**: Fuzzy-матчинг отелей между провайдерами
- [ ] **CMP-02**: Секция сравнения в отчёте
</requirements>
