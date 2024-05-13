FROM python:3.10-alpine

WORKDIR /app

ENV telegram_token=CHANGE_ME

RUN apk add --no-cache py3-pip
RUN pip install telegram
RUN pip install python-telegram-bot

COPY ./app .

EXPOSE 8080

CMD ["python", "main.py"]