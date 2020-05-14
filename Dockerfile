FROM python:3.6-alpine

WORKDIR /app

RUN apk update
RUN apk add git

ADD requirements.txt /app
RUN python -m pip install -r /app/requirements.txt

ADD bot /app/bot

# Make sure you make your configuration file available at this path.
CMD ["python", "-m", "bot", "--config", "/config/gvrd_grunt_config.json"]
