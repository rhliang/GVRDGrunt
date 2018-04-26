FROM python:3.6-alpine

WORKDIR /app

ADD . /app

RUN apk update
RUN apk add git
RUN python -m pip install -r requirements.txt

CMD ["python", "-m", "bot"]
