FROM python:3.11-slim

WORKDIR /app

COPY price_monitor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY price_monitor ./price_monitor

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "price_monitor.monitor"]
