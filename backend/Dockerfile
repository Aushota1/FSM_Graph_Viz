FROM python:3.11-slim

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бекенда
COPY main.py .

# Копируем модули FSM_Graph_Viz (будет скопировано через docker-compose volume)
# В docker-compose.yml настроен volume для FSM_Graph_Viz

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

