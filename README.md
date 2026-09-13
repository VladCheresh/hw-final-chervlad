# hw_final — Projects API

Итоговое домашнее задание по теме "Docker+FastAPI". Приложение на FastAPI с JWT-аутентификацией, CRUD для сущности `Project`, кешированием через Redis и хранением данных в PostgreSQL.

## GitHub репозиторий

https://github.com/VladCheresh/hw-final-chervlad

## Публичный URL (деплой на Render)

https://hw-final-chervlad.onrender.com

## Стек

- FastAPI (async)
- SQLAlchemy (async) + Alembic
- PostgreSQL
- Redis
- JWT (python-jose) + passlib (bcrypt)
- Pytest + httpx (тесты)
- Docker / Docker Compose

## Запуск локально (без Docker)

1. Создать и активировать виртуальное окружение:
   ```
   python -m venv venv
   source venv/Scripts/activate   # Windows (git bash)
   ```
2. Установить зависимости:
   ```
   pip install -r requirements.txt
   ```
3. Поднять PostgreSQL и Redis локально (например, через отдельные Docker-контейнеры) и указать переменные окружения (см. пример `.env` ниже).
4. Применить миграции:
   ```
   alembic upgrade head
   ```
5. Запустить сервер:
   ```
   uvicorn app.main:app --reload
   ```
6. Открыть документацию: http://127.0.0.1:8000/docs

## Запуск через Docker

1. Убедиться, что Docker Desktop запущен.
2. Собрать образы:
   ```
   docker-compose build
   ```
3. Запустить все сервисы (web, db, redis):
   ```
   docker-compose up
   ```
4. Применить миграции (в отдельном терминале, при первом запуске):
   ```
   docker-compose run web alembic upgrade head
   ```
5. Приложение доступно на http://localhost:8000/docs

При старте приложение автоматически создаёт тестового администратора:
- username: `admin`
- password: `admin12345`

## Запуск тестов

Тесты используют отдельную тестовую базу данных (`test-db`), чтобы не затрагивать основные данные.

```
docker-compose up -d test-db
docker-compose run web python -m pytest
```

## Пример .env

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/hw_final_chervlad
SYNC_DATABASE_URL=postgresql://postgres:postgres@db:5432/hw_final_chervlad
REDIS_URL=redis://redis:6379
SECRET_KEY=your_secret_key
```

## Эндпоинты

### Аутентификация

| Метод | Путь | Описание | Доступ |
|---|---|---|---|
| POST | `/register` | Регистрация нового аккаунта (роль всегда `user`) | Открытый |
| POST | `/login` | Логин, возвращает JWT-токен | Открытый |
| GET | `/me` | Данные текущего аккаунта (без пароля) | Авторизованный пользователь |
| GET | `/admin/stats` | Статистика по аккаунтам (всего/админов/пользователей) | Только роль `admin` |

### Проекты

| Метод | Путь | Описание | Доступ |
|---|---|---|---|
| POST | `/projects` | Создать проект (владелец — текущий пользователь) | Авторизованный пользователь |
| GET | `/projects` | Список всех проектов (кешируется в Redis на 60 сек) | Авторизованный пользователь |
| GET | `/projects/{id}` | Получить один проект по id | Авторизованный пользователь |
| PUT | `/projects/{id}` | Обновить проект | Только владелец проекта |
| DELETE | `/projects/{id}` | Удалить проект | Только владелец проекта |

### Коды ошибок

- `401 Unauthorized` — неверные логин/пароль, отсутствующий или недействительный токен
- `403 Forbidden` — доступ запрещён (не владелец проекта / не администратор)
- `404 Not Found` — запрошенный проект не существует
- `409 Conflict` — username или email уже заняты при регистрации
