# Megano — Интернет-магазин

Дипломный проект на Django.

## Развёртывание проекта

```bash
# 1. Клонировать репозиторий
git clone <url>
cd python_django_diploma

# 2. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Собрать и установить фронтенд-пакет
cd diploma-frontend
python setup.py sdist
pip install dist/diploma-frontend-0.6.tar.gz
cd ..

# 5. Настроить переменные окружения
cp .env.example .env
# Отредактировать .env — указать SECRET_KEY

# 6. Раскомментировать frontend в settings.py и urls.py
# INSTALLED_APPS: "frontend"
# urls.py: path("", include("frontend.urls"))

# 7. Применить миграции
python manage.py migrate

# 8. Запустить сервер
python manage.py runserver 0.0.0.0:8000
```

## Начальные данные

После `migrate` автоматически создаются:
- Суперпользователь: **admin** / **admin**
- Группы (роли): **Администратор**, **Покупатель**
- Настройки сайта (стоимость доставки, порог бесплатной доставки)

## Структура проекта

- `megano/` — настройки Django-проекта
- `shopapp/` — основное приложение (модели, API, админка)
- `diploma-frontend/` — фронтенд-пакет (Vue 3 + шаблоны)
