FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /srv/app/requirements.txt
RUN pip install --upgrade pip && pip install -r /srv/app/requirements.txt

COPY . /srv/app
COPY deploy/supervisord.railway.conf /etc/supervisor/conf.d/supervisord.conf

RUN mkdir -p /srv/app/runtime-data

EXPOSE 8000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
