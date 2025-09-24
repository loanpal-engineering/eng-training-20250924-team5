FROM python:3.10-slim

# Install system dependencies for mysqlclient, git, and other tools
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    mariadb-client \
    coreutils \
    curl \
    git \
    socat \
    && rm -rf /var/lib/apt/lists/*

# Create app directory and set as working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

RUN pip install -r requirements.txt \
    && pip install bcrypt

COPY init.local.sql .

RUN useradd -m vulnleap

COPY . .

# Switch to the vulnleap user
USER vulnleap

EXPOSE 5555

CMD ["gunicorn", "--bind", "0.0.0.0:5555", "--reload", "--workers", "1", "--pythonpath", "/app", "wsgi:app"]