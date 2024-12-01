FROM homeassistant/amd64-base-python:3.11-alpine3.18
WORKDIR /app

# Install required packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    gcc \
    musl-dev \
    python3-dev

# Copy your application
COPY cctvai /app/cctvai
COPY rootfs /

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    discord.py \
    pillow \
    requests

# Run the application
CMD [ "python3", "-u", "/app/cctvai/app.py" ]
