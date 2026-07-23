FROM python:3.10-slim

RUN adduser --disabled-password --gecos "" appuser

WORKDIR /app
ENV PYTHONPATH=/app:${PYTHONPATH}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER appuser

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
