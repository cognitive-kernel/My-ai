FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pyproject.toml .
COPY my_ai my_ai
COPY docs docs
RUN useradd --create-home --uid 10001 myai && mkdir -p /app/data /app/projects /app/self-repair && chown -R myai:myai /app
USER myai
ENV HOST=0.0.0.0
ENV PORT=8000
EXPOSE 8000
CMD ["python","-m","my_ai"]
