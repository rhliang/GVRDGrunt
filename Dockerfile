FROM python:3.6-alpine

WORKDIR /app

ADD bot /app
ADD requirements.txt /app

RUN apk update
RUN apk add git
RUN python -m pip install -r /app/requirements.txt

# Make sure you make your configuration file available at this path.
CMD ["python", "-m", "bot", "--config", "/config/gvrd_grunt_config.json"]
