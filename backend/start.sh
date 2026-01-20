#!/bin/bash

# Dr. Melton Backend - Quick Start Script
# This script starts all services and runs the backend server

set -e  # Exit on error

echo "🚀 Dr. Melton Backend - Quick Start"
echo "===================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please copy .env.example to .env and configure it."
    exit 1
fi

# Start Docker services
echo "📦 Starting Docker services (PostgreSQL)..."
docker-compose up -d

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker exec melton_postgres pg_isready -U melton > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ PostgreSQL failed to start"
        exit 1
    fi
    sleep 1
done

# Check if alembic versions directory exists
if [ ! -d "alembic/versions" ]; then
    echo "📁 Creating alembic versions directory..."
    mkdir -p alembic/versions
fi

# Run database migrations
echo "🗄️  Running database migrations..."
poetry run alembic upgrade head

echo ""
echo "✅ All services are ready!"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "🌐 Starting backend server..."
echo "   - API: http://localhost:8000"
echo "   - Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the backend server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
