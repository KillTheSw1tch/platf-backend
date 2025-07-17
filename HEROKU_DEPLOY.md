# Деплой на Heroku

## Що було додано для деплою:

### 1. **Procfile**
- Вказує Heroku як запускати Django додаток
- Використовує gunicorn для production

### 2. **runtime.txt**
- Вказує версію Python (3.11.7)

### 3. **app.json**
- Опис додатку для Heroku
- Налаштування змінних середовища
- Додатки PostgreSQL та Redis

### 4. **Оновлені налаштування Django**
- Підтримка PostgreSQL через `dj-database-url`
- WhiteNoise для статичних файлів
- Змінні середовища для секретних даних
- Налаштування Redis для WebSocket

### 5. **Оновлений requirements.txt**
- Додано `whitenoise` та `dj-database-url`

## Кроки для деплою:

### 1. Підготовка
```bash
# Встановіть Heroku CLI
# Зареєструйтесь на heroku.com
# Увійдіть в CLI
heroku login
```

### 2. Створення додатку
```bash
# Створіть новий додаток
heroku create your-app-name

# Або використайте існуючий
heroku git:remote -a your-app-name
```

### 3. Налаштування змінних середовища
```bash
# Встановіть змінні середовища
heroku config:set SECRET_KEY="your-secret-key"
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS="your-app-name.herokuapp.com"
```

### 4. Додавання бази даних
```bash
# Додайте PostgreSQL
heroku addons:create heroku-postgresql:mini

# Додайте Redis (якщо потрібно)
heroku addons:create heroku-redis:mini
```

### 5. Налаштування buildpacks
```bash
# Додайте Python buildpack
heroku buildpacks:set heroku/python

# Додайте Node.js buildpack (для frontend)
heroku buildpacks:add heroku/nodejs
```

### 6. Деплой
```bash
# Закомітьте зміни
git add .
git commit -m "Prepare for Heroku deployment"

# Задеплойте
git push heroku main
```

### 7. Міграції бази даних
```bash
# Запустіть міграції
heroku run python manage.py migrate

# Створіть суперкористувача
heroku run python manage.py createsuperuser
```

### 8. Збірка статичних файлів
```bash
# Зберіть статичні файли
heroku run python manage.py collectstatic --noinput
```

## Важливі моменти:

### 1. **Замініть назву додатку**
- У `app.json` замініть `your-app-name` на реальну назву
- У `settings.py` оновіть `CORS_ALLOWED_ORIGINS`

### 2. **Налаштування frontend**
- Frontend буде збиратися в `frontend/dist/`
- Django буде обслуговувати статичні файли

### 3. **База даних**
- SQLite замінюється на PostgreSQL
- Дані з локальної бази не переносяться автоматично

### 4. **Файли медіа**
- Для збереження файлів використовуйте AWS S3 або подібні сервіси
- Локальна папка `media/` не зберігається на Heroku

### 5. **Логи**
```bash
# Перегляньте логи
heroku logs --tail
```

## Структура після деплою:

```
your-app-name.herokuapp.com/
├── /api/          # Django API endpoints
├── /admin/        # Django admin
├── /static/       # Статичні файли (CSS, JS, images)
└── /media/        # Медіа файли (якщо налаштовано)
```

## Troubleshooting:

### Помилка з статичними файлами:
```bash
heroku run python manage.py collectstatic --noinput
```

### Помилка з базою даних:
```bash
heroku run python manage.py migrate
```

### Помилка з портом:
- Heroku автоматично встановлює `$PORT`
- Gunicorn налаштований правильно

### Помилка з Redis:
- Перевірте, чи додано Redis addon
- Перевірте `REDIS_URL` в змінних середовища 