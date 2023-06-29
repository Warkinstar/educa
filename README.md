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

* Добавьте группу "Преподаватели" на сайте администратора и дайте все права связанные с courses http://127.0.0.1:8000/admin/
![educa teachers group](https://storage.googleapis.com/bucket-django-educa/images/educa_teachers.png?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=educaproject%40educa-django-storages.iam.gserviceaccount.com%2F20230629%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20230629T102211Z&X-Goog-Expires=86400&X-Goog-SignedHeaders=host&X-Goog-Signature=086dc142bd3b0f2ae6ebc973749de20ce42dd062c1a125ac38921e25e124d1d3beb4d419d6c96d193c00391a8c34f6d348fe76ad15f4cf052a0e29977ff40574614e0aead6b38362d50a16203b930994016f9b7eeb2501e97b6269624c16717e22758dde95cbd70be307048f41439fed90ae1e066e3081d8db19e911122582100542d7746fce661603fa11d3d3667cf6a14bb2b49318634a5358de1c163aeaaf557111e0009b2f46dded77724179f63521b481bb698dc56a3101362c0230fc68d4ee0d502f9eb9029a1d92922586d408da6698c6d2a1f312d659a85b11f5954bb5c62b211b92ab5a17723b6ade685659114893318f392eaaf9a3710a5cbc4a25)

* Добавьте пользователя в группу:
  ![user group grand](https://storage.googleapis.com/bucket-django-educa/images/user_group_grand.png?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=educaproject%40educa-django-storages.iam.gserviceaccount.com%2F20230629%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20230629T104410Z&X-Goog-Expires=86400&X-Goog-SignedHeaders=host&X-Goog-Signature=8583aa81440b97e58110e2d654a4267ed760edbaa29e48c1454edb02d2317cc93c9b3216b65e8c0e3131cc570b7136fdbd867f4ebcf1ab31fd407a43986025cac7c4be837baee21190f2ef7de9aab28b3368ed0af8306c63e62a7086d54e3953751168a8e39e288fb4cd289d5f8fa73d045aab28f320458737c9b491d2590c5e27a40eeab44f8a50020a48cce6f9f84de4a37a457e792f8949cf7484ae49b3177a13ece89918f7fb93b9b43e100f64fa31a4136265085cf440ae10b96333b138c8b345f1e26c54e1e1ea60e13cc134d462ffd54f68dc4ed735949322178c047b43a045a13a3975f7238b83a81d5f4667c4c501728f30a156a08ff7487cdff02e)

После этого пользователь может добавлять свои собственные курсы на сайт

## Лицензия

Этот проект лицензирован в соответствии с лицензией MIT. Подробности можно найти в файле [LICENSE](LICENSE).

