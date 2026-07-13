FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY examples ./examples

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["python", "-m", "telemetry_analyzer.api", "--host", "0.0.0.0", "--port", "8080"]
