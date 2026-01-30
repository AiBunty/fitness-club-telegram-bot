FROM python:3.11-slim

WORKDIR /app

COPY . /app

# Install dependencies
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r fitness-club-telegram-bot/requirements.txt \
    && pip install supervisor

# Expose port for health check (Flask default 5000)
EXPOSE 5000

# Copy supervisor config
COPY fitness-club-telegram-bot/supervisord.conf /etc/supervisord.conf

# Start both bot and health check
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
