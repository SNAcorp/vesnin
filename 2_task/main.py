import os
from typing import List, Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
from pydantic import BaseModel
from starlette.responses import JSONResponse

app = FastAPI()

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Инициализируем шаблоны
templates = Jinja2Templates(directory="templates")

# Путь к CSV файлу из переменной окружения
CSV_PATH = os.getenv("CSV_PATH", "data/database.csv")


class User(BaseModel):
    id: str
    name: str
    surname: str
    second_name: str
    email: str
    phone_number: str

    class Config:
        from_attributes = True


def get_data() -> List[Dict[str, str]]:
    try:
        df = pd.read_csv(CSV_PATH)
        # Удаляем пробелы из названий столбцов
        df.columns = df.columns.str.strip()
        # Преобразуем все значения в строки и удаляем пробелы
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        return df.to_dict('records')
    except FileNotFoundError:
        return []


def get_user_by_id(user_id: str) -> Dict[str, str] | None:
    data = get_data()
    for user in data:
        if str(user.get('id')) == user_id:
            return user
    return None


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    data = get_data()
    return templates.TemplateResponse(
        "base.html",
        {"request": request, "data": data}
    )


@app.get("/api/users", response_model=List[User])
async def get_users():
    return get_data()


@app.get("/api/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail=f"Пользователь с ID {user_id} не найден"
        )
    return user


@app.get("/api/data")
async def get_json_data() -> List[Dict[str, str]]:
    try:
        df = pd.read_csv(CSV_PATH)
        # Удаляем пробелы из названий столбцов
        df.columns = df.columns.str.strip()
        # Преобразуем все значения в строки и удаляем пробелы
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        return df.to_dict('records')
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Файл с данными не найден"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при чтении данных: {str(e)}"
        )
