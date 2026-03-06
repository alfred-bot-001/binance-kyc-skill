FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Copy config
COPY .env.example .env.example

# Create data directory
RUN mkdir -p data/sessions data/uploads

# Non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8443

ENTRYPOINT ["binance-kyc"]
CMD ["run"]
