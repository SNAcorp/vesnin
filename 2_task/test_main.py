from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest
from fastapi import HTTPException, UploadFile
from starlette.requests import Request

# Импортируем непосредственно функции из модуля (предполагается, что ваш код лежит в файле main.py)
from main import get_users, get_user, get_json_data, read_root, upload_csv, append_to_csv, validate_csv_structure


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


VALID_CSV_CONTENT = """id,name,surname,second_name,email,phone_number,additional_field
1,Иван,Иванов,Иванович,ivan@test.com,+79001234567,test
2,Петр,Петров,Петрович,petr@test.com,+79001234568,test"""

INVALID_STRUCTURE_CSV = """id,name,surname,email
1,Иван,Иванов,ivan@test.com
2,Петр,Петров,petr@test.com"""

DUPLICATE_IDS_CSV = """id,name,surname,second_name,email,phone_number
1,Иван,Иванов,Иванович,ivan@test.com,+79001234567
1,Петр,Петров,Петрович,petr@test.com,+79001234568"""

MOCK_CSV_PATH = "test_data/users.csv"


# Тесты для validate_csv_structure
class TestCSVValidation:
    def test_valid_csv_structure(self):
        """Проверяет, что валидный CSV файл проходит проверку структуры"""
        assert validate_csv_structure(VALID_CSV_CONTENT) is True

    def test_invalid_csv_structure(self):
        """Проверяет, что CSV с неполным набором колонок не проходит валидацию"""
        assert validate_csv_structure(INVALID_STRUCTURE_CSV) is False

    def test_empty_csv(self):
        """Проверяет обработку пустого CSV файла"""
        assert validate_csv_structure("") is False

    def test_invalid_csv_format(self):
        """Проверяет обработку некорректного формата CSV"""
        assert validate_csv_structure("not,a,valid\ncsv,file") is False


# Тесты для append_to_csv
class TestCSVAppend:
    @pytest.fixture(autouse=True)
    def setup_cleanup(self, tmp_path):
        """Фикстура для создания временной директории и очистки тестовых файлов"""
        # Создаем временную директорию для тестов
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()
        self.test_file = str(test_dir / "users.csv")
        yield
        # Очистка не требуется, tmp_path очищается автоматически

    def test_append_to_new_file(self):
        """Проверяет создание нового файла с данными"""
        with patch('main.CSV_PATH', self.test_file):
            assert append_to_csv(VALID_CSV_CONTENT) is True
            df = pd.read_csv(self.test_file)
            assert len(df) == 2
            assert set(df['id']) == {1, 2}

    def test_append_with_duplicates(self):
        """Проверяет обработку дубликатов при добавлении данных"""
        with patch('main.CSV_PATH', self.test_file):
            append_to_csv(VALID_CSV_CONTENT)
            append_to_csv(DUPLICATE_IDS_CSV)

            df = pd.read_csv(self.test_file)
            assert len(df) == 2
            assert len(df[df['name'] == 'Петр']) == 1

    def test_append_to_existing_file(self):
        """Проверяет добавление данных к существующему файлу"""
        with patch('main.CSV_PATH', self.test_file):
            append_to_csv(VALID_CSV_CONTENT)
            new_content = """id,name,surname,second_name,email,phone_number
3,Сидор,Сидоров,Сидорович,sidor@test.com,+79001234569"""
            append_to_csv(new_content)

            df = pd.read_csv(self.test_file)
            assert len(df) == 3
            assert set(df['id']) == {1, 2, 3}


# Тесты для API endpoint
class TestUploadEndpoint:
    @pytest.mark.asyncio
    async def test_upload_valid_csv(self, tmp_path):
        """Проверяет успешную загрузку валидного CSV файла"""
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=VALID_CSV_CONTENT.encode('utf-8'))

        test_file = str(tmp_path / "users.csv")
        with patch('main.CSV_PATH', test_file):
            result = await upload_csv(mock_file)
            assert result == {"message": "Файл успешно загружен"}

    @pytest.mark.asyncio
    async def test_upload_invalid_structure(self):
        """Проверяет отклонение CSV файла с неверной структурой"""
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=INVALID_STRUCTURE_CSV.encode('utf-8'))

        try:
            await upload_csv(mock_file)
            pytest.fail("Expected HTTPException was not raised")
        except HTTPException as exc:
            assert exc.status_code == 400
            assert "Неверная структура CSV файла" in exc.detail

    @pytest.mark.asyncio
    async def test_upload_save_error(self):
        """Проверяет обработку ошибки при сохранении файла"""
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=VALID_CSV_CONTENT.encode('utf-8'))

        with patch('main.append_to_csv', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await upload_csv(mock_file)

            assert exc_info.value.status_code == 500
            assert "Ошибка при сохранении данных" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_upload_read_error(self):
        """Проверяет обработку ошибки при чтении файла"""
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(side_effect=Exception("Read error"))

        with pytest.raises(HTTPException) as exc_info:
            await upload_csv(mock_file)

        assert exc_info.value.status_code == 500
        assert "Ошибка при загрузке файла" in exc_info.value.detail
