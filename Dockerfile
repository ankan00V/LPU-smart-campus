FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

COPY requirements.txt /srv/app/requirements.txt
RUN pip install --upgrade pip && pip install -r /srv/app/requirements.txt

COPY . /srv/app

RUN mkdir -p /srv/app/runtime-data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
