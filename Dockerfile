FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=2718

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
COPY docs ./docs
COPY notebooks ./notebooks
COPY server.py ./

# editable, so that the package keeps finding data/ next to src/
RUN pip install --no-cache-dir -e .

EXPOSE 2718

CMD ["sh", "-c", "python -m uvicorn server:app --host 0.0.0.0 --port ${PORT:-2718}"]
