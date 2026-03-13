FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1
RUN useradd -u 10001 -m appuser
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN mkdir -p /var/log/dir-cleaner && chown -R appuser:appuser /var/log/dir-cleaner
EXPOSE 8080
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
