 
FROM python:3.8.6

LABEL MAINTAINER="dkeysil dkeysil@protonmail.com"

WORKDIR /eventerbot
ADD ./requirements.txt /eventerbot/requirements.txt
RUN pip install -r requirements.txt
ADD . /eventerbot

CMD python -u __main__.py
