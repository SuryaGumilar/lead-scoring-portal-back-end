FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .

# install requirement (bcrypt compile friendly)
RUN pip install --no-cache-dir --no-binary=bcrypt bcrypt==4.3.0 -r requirements.txt

COPY . .

ENV PORT=8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
