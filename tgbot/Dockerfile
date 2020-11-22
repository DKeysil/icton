 
FROM python:3.8.6

LABEL MAINTAINER="dkeysil dkeysil@protonmail.com"

WORKDIR /nvsywbot
ADD ./requirements.txt /nvsywbot/requirements.txt
RUN pip install -r requirements.txt
ADD . /nvsywbot

CMD python -u __main__.py
