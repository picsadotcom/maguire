FROM ghcr.io/praekeltfoundation/docker-django-bootstrap-nw:py3.10-bullseye

COPY . /app
RUN pip install -r requirements.txt
RUN pip install -e .

ENV SENTRY_RELEASE=${VCS_HASH}
ENV DJANGO_SETTINGS_MODULE maguire.settings
ENV CELERY_APP maguire

RUN django-admin collectstatic --noinput
CMD ["maguire.wsgi:application", "--workers", "2", "--threads", "3", "--timeout", "420", "--max-requests", "1000", "--max-requests-jitter", "100", "--graceful-timeout", "300"]
