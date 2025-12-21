#!/bin/bash

# Dr. Melton Frontend - Quick Start Script

set -e  # Exit on error

echo "🚀 Dr. Melton Frontend - Quick Start"
echo "===================================="
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "⚠️  Warning: Backend server doesn't seem to be running at http://localhost:8000"
    echo "   Please start the backend first (cd ../backend && ./start.sh)"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if .env.local exists, create if not
if [ ! -f .env.local ]; then
    echo "📝 Creating .env.local file..."
    cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
    echo "✅ Created .env.local with default settings"
    echo ""
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

echo "✅ Frontend is ready!"
echo ""
echo "🌐 Starting frontend server..."
echo "   - App: http://localhost:3000"
echo "   - Agents: http://localhost:3000/agents"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the frontend server
npm run dev
