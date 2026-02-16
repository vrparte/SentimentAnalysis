#!/bin/bash
# Setup script for Director Media Monitoring

echo "Setting up Director Media Monitoring..."

# Create .env from example if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit .env and configure your settings"
fi

# Create storage directory
mkdir -p storage

# Build and start services
echo "Building Docker images..."
docker compose build

echo "Starting services..."
docker compose up -d

# Wait for database to be ready
echo "Waiting for database..."
sleep 5

# Run migrations
echo "Running database migrations..."
docker compose exec api alembic upgrade head

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Create admin user: docker compose exec api python -m app.cli create-admin"
echo "3. Seed directors: docker compose exec api python -m app.seed directors.yaml"
echo "4. Access dashboard: http://localhost:8000"

