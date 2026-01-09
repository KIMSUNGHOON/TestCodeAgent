#!/bin/bash
# Agentic Coder Server Startup Script
# Starts the FastAPI server accessible from external machines

set -e

echo "🚀 Starting Agentic Coder Server..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✓ Created .env - Please edit it with your configuration"
        echo ""
    else
        echo "❌ Error: .env.example not found"
        exit 1
    fi
fi

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
fi

# Get local IP address for display
LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "unknown")

echo ""
echo "✅ Server Configuration:"
echo "   - Local access:    http://localhost:8000"
echo "   - Network access:  http://${LOCAL_IP}:8000"
echo "   - API docs:        http://localhost:8000/docs"
echo "   - Health check:    http://localhost:8000/health"
echo ""
echo "🌐 Server will be accessible from other machines on your network"
echo "   Use this for remote client: ${LOCAL_IP}:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start server with external access enabled
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
