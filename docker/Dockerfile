FROM bitnami/spark:latest

USER root

# Optional: install Python deps
RUN apt-get update && apt-get install -y python3-pip
RUN pip3 install pyyaml fire pandas

WORKDIR /app
COPY . /app
