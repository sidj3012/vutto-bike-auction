FROM python:3.12-slim
WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home appuser && chown -R appuser:appuser /srv
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "python -m app.worker & exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
