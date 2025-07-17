from setuptools import setup, find_packages

setup(
    name="platforma-backend",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "asgiref",
        "Django",
        "django-cors-headers",
        "djangorestframework",
        "djangorestframework-simplejwt",
        "PyJWT",
        "pytz",
        "sqlparse",
        "psycopg2-binary",
        "python-dotenv",
        "channels",
        "channels-redis",
        "Pillow",
        "pyotp",
        "qrcode",
        "requests",
        "gunicorn",
        "whitenoise",
        "dj-database-url",
    ],
) 