FROM python:3.10-slim

WORKDIR /app

COPY focuspilot-backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY focuspilot-backend/ ./

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
