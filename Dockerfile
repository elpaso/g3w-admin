FROM ubuntu:bionic
LABEL maintainer="Gis3w" Description="This image is used to install requirements for g3w-suite CI testing" Vendor="Gis3w" Version="1.0"
RUN chown root:root /tmp && chmod ugo+rwXt /tmp
RUN apt-get update && apt install -y libgdal20 python-gdal python-pip curl wget vim wait-for-it
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - && \
    echo "deb https://dl.yarnpkg.com/debian/ stable main" | \
    tee /etc/apt/sources.list.d/yarn.list
RUN apt-get update && apt install -y yarn
RUN mkdir /code
WORKDIR /code
COPY requirements*.* /code/
RUN pip install -r requirements_docker.txt
COPY . /code/
