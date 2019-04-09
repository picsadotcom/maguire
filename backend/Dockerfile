FROM praekeltfoundation/django-bootstrap:py3.6-jessie

COPY . /app
RUN pip install -e .

ENV SENTRY_RELEASE=${VCS_HASH}
ENV DJANGO_SETTINGS_MODULE maguire.settings
ENV CELERY_APP maguire

RUN django-admin collectstatic --noinput
CMD ["maguire.wsgi:application", "--threads", "5", "--timeout", "300"]
