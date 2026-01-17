#!/bin/bash

# Bifrost Docs - Development Environment Launcher
# Starts the full stack with hot reload enabled

set -e

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "   Run ./setup.sh first to configure your environment."
    exit 1
fi

echo "🚀 Starting Bifrost Docs development environment..."
echo ""
echo "Services:"
echo "  • PostgreSQL (pgvector) - localhost:5433"
echo "  • Redis                 - localhost:6380"
echo "  • MinIO Console         - localhost:9001"
echo "  • PgBouncer             - localhost:6433"
echo "  • API (hot reload)      - proxied through client"
echo "  • Client (hot reload)   - localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
