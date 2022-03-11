FROM python:3.8-buster as base

FROM base as builder
RUN adduser --disabled-password --gecos '' frege
ENV PYTHONUNBUFFERED 1
COPY --chown=frege requirements.txt /tmp/

COPY --chown=frege ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt

FROM builder as dev
WORKDIR /app
COPY . .

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "main.py"]
