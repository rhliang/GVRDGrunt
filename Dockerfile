FROM python:3.6-alpine

WORKDIR /app

ADD bot /app

RUN apk update
RUN apk add git
RUN python -m pip install -r requirements.txt
# For Docker, use the standard settings_docker.py as the settings file.
RUN ["cp", "/app/bot/settings_docker.py", "/app/bot/settings.py"]

CMD ["python", "-m", "bot"]
