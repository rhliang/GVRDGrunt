FROM python:3.6-slim

WORKDIR /app

ADD . /app

RUN python -m pip install -r requirements.txt

CMD ["python", "-m", "bot"]