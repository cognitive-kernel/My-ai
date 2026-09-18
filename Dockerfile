FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY my_ai my_ai
RUN useradd --create-home --uid 10001 myai && mkdir -p /app/data && chown -R myai:myai /app
USER myai
EXPOSE 8000
CMD ["python","-m","my_ai"]
