# educa
**E-learning Platform**
### https://educa-project.fly.dev/

Электронная платформа для обучения предоставляющая возможность создавать собственные курсы, возможность 
записываться/отписываться, управлять курсами, для каждого курса интегрирован чат для общения между студентами
и преподователем курса. Курс делится на модули, модули заполняются содержимым-контентами. Контенты 
бывают разным типов это: текстовый редактор, изображения, видео в виде ссылок на youtube, тесты для 
проверки знаний, задания где студент должен прикрепить ответ в течении определенного срока если преподователь
ограничил время. Задания и Тесты могут оценивать студентов по бальной шкале.

# Установка

* Создаем виртуальное окружение
```
python -m venv .venv
.venv/scripts/activate
```

* Устанавливаем зависимости проекта
pip install -r requirements.txt

* Создайте файл .env для установки переменных сред:
```env
# .env
DEBUG = True
SECRET_KEY = your_secret_key_50_symbols
REDIS_URL = "redis://127.0.0.1:6379"


DJANGO_SECURE_SSL_REDIRECT = False


DJANGO_SECURE_HSTS_SECONDS = 0
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS = False
DJANGO_SECURE_HSTS_PRELOAD = False


DJANGO_SESSION_COOKIE_SECURE = False
DJANGO_CSRF_COOKIE_SECURE = False

# Google SMPT
EMAIL_HOST_USER = "your_smpt_email"
EMAIL_HOST_PASSWORD = "your_password"
```

* Можете расскоментировать в educa/settings.py, чтобы использовать вывод smpt сообщений в консоль

```python
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```
В режиме Debug == True хранилище медиа файлов будет локальным, иначе вам придется указать свои данные корзины Google Storage Cloud

* Установите и запустите redis (необходимо чтобы был установлен Docker)
```
docker pull redis
docer run --name redis -p 6379:6379 redis
```

* Проведите миграцию базы данных:
```
python manage.py migrate
```

* Создайте superuser:
```
python manage.py creatsuperuser
```

* Запуск проекта:
```
python manage.py runserver
```

Добавьте группу "Преподаватели" на сайте администратора и дайте все права связанные с courses http://127.0.0.1:8000/admin/
![educa teachers group](https://drive.google.com/file/d/1qYf7dOdNC6UOfWkMAG_U3-FtRYjD1Z1T/view?usp=sharing)
