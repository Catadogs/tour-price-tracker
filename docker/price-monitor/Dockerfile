FROM python:3.11-slim

WORKDIR /app

COPY price_monitor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY price_monitor ./price_monitor

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "price_monitor.monitor"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import sqlite3, os; con = sqlite3.connect(os.environ.get('BG_DB_PATH', '/data/price_monitor.sqlite3')); con.execute('SELECT 1'); con.close()" || exit 1
