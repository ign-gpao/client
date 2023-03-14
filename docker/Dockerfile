FROM library/python:latest
LABEL maintainer="IGN"
LABEL version="0.13.0"

ADD . /var/client

WORKDIR /var/client

RUN ls -lh

RUN pip install -r requirements.txt