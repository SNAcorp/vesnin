import pytest
from fastapi import HTTPException
from starlette.requests import Request

# Импортируем непосредственно функции из модуля (предполагается, что ваш код лежит в файле main.py)
from main import get_users, get_user, get_json_data, read_root


def dummy_request():
    """
    Создаёт фиктивный объект Request с минимальной конфигурацией.
    """
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b'',
        "client": ("127.0.0.1", 8000),
        "server": ("127.0.0.1", 8000),
    }
    return Request(scope)


@pytest.fixture
def sample_csv(tmp_path, monkeypatch):
    """
    Фикстура для создания временного CSV-файла с тестовыми данными и
    подмены глобальной переменной CSV_PATH в модуле main.
    """
    csv_content = (
        "id,name,surname,second_name,email,phone_number\n"
        "1,Иван,Иванов,Иванович,ivan@example.com,1111111111\n"
        "2,Петр,Петров,Петрович,petrov@example.com,2222222222\n"
    )
    file_path = tmp_path / "test.csv"
    file_path.write_text(csv_content, encoding="utf-8")

    # Подменяем CSV_PATH в модуле main
    import main
    monkeypatch.setattr(main, "CSV_PATH", str(file_path))
    return file_path


# @pytest.mark.asyncio
# async def test_read_root(sample_csv):
#     """
#     Тестируем эндпоинт "/" напрямую.
#     Вызываем read_root, рендерим шаблон и проверяем, что в полученном HTML есть хотя бы одно имя.
#     """
#     request = dummy_request()
#     response = await read_root(request)
#     # Рендерим шаблон, чтобы получить содержимое ответа
#     await response.render()
#     body = response.body.decode("utf-8")
#     assert "Иван" in body or "Петр" in body


@pytest.mark.asyncio
async def test_get_users(sample_csv):
    """
    Тестируем эндпоинт /api/users, который возвращает список пользователей.
    """
    response = await get_users()
    assert isinstance(response, list)
    assert len(response) == 2
    assert response[0]["id"] == "1"


@pytest.mark.asyncio
async def test_get_user_valid(sample_csv):
    """
    Тестируем эндпоинт /api/users/{user_id} с корректным ID.
    """
    user = await get_user("1")
    assert user["id"] == "1"
    assert user["name"] == "Иван"


@pytest.mark.asyncio
async def test_get_user_invalid(sample_csv):
    """
    Тестируем эндпоинт /api/users/{user_id} с несуществующим ID.
    Ожидаем, что будет выброшено исключение HTTPException с кодом 404.
    """
    with pytest.raises(HTTPException) as exc_info:
        await get_user("999")
    assert exc_info.value.status_code == 404
    assert "Пользователь с ID 999 не найден" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_json_data(sample_csv):
    """
    Тестируем эндпоинт /api/data, возвращающий данные в формате JSON.
    """
    data = await get_json_data()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_file_not_found(monkeypatch):
    """
    Тестируем ситуацию, когда CSV-файл не найден.
    Подменяем CSV_PATH на несуществующий путь и проверяем, что вызывается HTTPException с кодом 404.
    """
    import main
    monkeypatch.setattr(main, "CSV_PATH", "non_existent.csv")
    with pytest.raises(HTTPException) as exc_info:
        await get_json_data()
    assert exc_info.value.status_code == 404
    assert "Файл с данными не найден" in exc_info.value.detail
