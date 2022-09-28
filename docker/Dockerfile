FROM library/python:latest
LABEL maintainer="IGN"
LABEL version="0.5.1"

ADD . /var/client

WORKDIR /var/client

RUN ls -lh

RUN pip install -r requirements.txt