import io
import os
from typing import List, Dict

from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
from pydantic import BaseModel
from starlette.responses import JSONResponse, RedirectResponse

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


def validate_csv_structure(file_content: str) -> bool:
    """Проверяет структуру CSV файла"""
    required_columns = {'id', 'name', 'surname', 'second_name', 'email', 'phone_number'}

    try:
        df = pd.read_csv(io.StringIO(file_content))
        columns = set(df.columns.str.strip())
        return required_columns.issubset(columns)
    except Exception:
        return False


def append_to_csv(file_content: str) -> bool:
    """
    Добавляет данные в CSV файл.
    Удаляет дубликаты по номеру телефона, оставляя последнюю версию записи.
    """
    try:
        # Создаем директорию, если она не существует
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)

        # Определяем обязательные колонки
        required_columns = [
            'id', 'name', 'surname', 'second_name', 'email', 'phone_number'
        ]

        # Читаем новые данные
        new_df = pd.read_csv(io.StringIO(file_content))

        # Очищаем номера телефонов от пробелов и '+' для корректного сравнения
        new_df['phone_number'] = new_df['phone_number'].astype(str).str.strip().str.replace('+', '')

        if os.path.exists(CSV_PATH):
            # Читаем существующие данные
            existing_df = pd.read_csv(CSV_PATH)
            existing_df['phone_number'] = existing_df['phone_number'].astype(str).str.strip().str.replace('+', '')

            # Объединяем данные
            final_df = pd.concat([existing_df, new_df], ignore_index=True)

            # Удаляем дубликаты по номеру телефона, оставляя последнюю запись
            final_df = final_df.drop_duplicates(subset=['phone_number'], keep='last')
        else:
            # Если файла нет, просто удаляем дубликаты в новых данных
            final_df = new_df.drop_duplicates(subset=['phone_number'], keep='last')

        # Проверяем наличие всех обязательных колонок
        for col in required_columns:
            if col not in final_df.columns:
                final_df[col] = None

        # Сохраняем результат
        final_df.to_csv(CSV_PATH, index=False)
        return True

    except Exception as e:
        print(f"Error in append_to_csv: {e}")
        return False


@app.get("/users", response_class=HTMLResponse)
async def read_root(request: Request):
    data = get_data()
    return templates.TemplateResponse(
        "users.html",
        {"request": request, "data": data}
    )


@app.get("/", response_class=RedirectResponse)
async def read_root():
    return RedirectResponse(url="/users")


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


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse(
        "upload.html",
        {"request": request}
    )


@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Загрузка CSV файла"""
    try:
        content = await file.read()
        content_str = content.decode('utf-8')

        if not validate_csv_structure(content_str):
            raise HTTPException(
                status_code=400,
                detail="Неверная структура CSV файла"
            )

        if not append_to_csv(content_str):
            raise HTTPException(
                status_code=500,
                detail="Ошибка при сохранении данных"
            )

        return {"message": "Файл успешно загружен"}
    except HTTPException:
        # Пробрасываем HTTPException без изменений
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при загрузке файла: {str(e)}"
        )


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
