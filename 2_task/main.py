import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd

app = FastAPI()

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Инициализируем шаблоны
templates = Jinja2Templates(directory="templates")

# Путь к CSV файлу из переменной окружения
CSV_PATH = os.getenv("CSV_PATH", "data/database.csv")


def get_data():
    """Функция для чтения данных из CSV файла"""
    try:
        df = pd.read_csv(CSV_PATH)
        return df.to_dict('records')
    except FileNotFoundError:
        return []


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Главная страница"""
    data = get_data()
    return templates.TemplateResponse(
        "base.html",
        {"request": request, "data": data}
    )
