FROM python:3.9-slim
WORKDIR /app
COPY cctvai/requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "cctvai/app.py"]
