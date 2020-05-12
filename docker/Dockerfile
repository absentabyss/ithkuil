FROM python:3.8.2-alpine3.11
MAINTAINER Agna

RUN apk add git gcc musl-dev && git clone https://github.com/absentabyss/ithkuil.git && cd ithkuil && pip install -r requirements.txt && apk del git gcc musl-dev

WORKDIR /ithkuil
CMD ["python", "-u", "gloss_bot.py"]
