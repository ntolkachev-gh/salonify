web: gunicorn salonify.wsgi:application --log-file -
worker: celery -A salonify worker --loglevel=info
beat: celery -A salonify beat --loglevel=info 