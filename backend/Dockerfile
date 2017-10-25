FROM westerncapelabs/docker-django-bootstrap
ARG VCS_HASH=NOT_SET
ENV SENTRY_RELEASE=${VCS_HASH}
ENV DJANGO_SETTINGS_MODULE "maguire.settings"
RUN ./manage.py collectstatic --noinput
ENV APP_MODULE "maguire.wsgi:application"
