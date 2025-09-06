FROM python:3.13-alpine
RUN mkdir /app
WORKDIR /app


# NOTE: test
# Set environment variables 
# Prevents Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 

# utils
RUN apk add --no-cache \
    build-base \
    libpq-dev \
    mariadb-connector-c-dev \
    jpeg-dev \
    zlib-dev \
    linux-headers \
    curl \
    bash

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv

COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev



COPY . /app/

EXPOSE 8000


# FIX: use prod server
CMD ["sh", "-c", "uv run python manage.py migrate && uv run python manage.py runserver 0.0.0.0:8000"]
