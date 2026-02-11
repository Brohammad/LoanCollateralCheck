#!/bin/bash
# Quick Start Script for AI Agent Workflow System

set -e  # Exit on error

echo "🚀 AI Agent Workflow System - Quick Start"
echo "=========================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Found Python $PYTHON_VERSION"

# Check if .env exists
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and set your GOOGLE_API_KEY"
    echo "   Get your API key at: https://ai.google.dev/"
    echo ""
    read -p "Press Enter to continue after setting your API key..."
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo ""
    echo "🔧 Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "🔌 Activating virtual environment..."
source .venv/bin/activate
echo "✓ Virtual environment activated"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✓ Dependencies installed"

# Create data directory
echo ""
echo "📁 Creating data directory..."
mkdir -p data
echo "✓ Data directory ready"

# Run tests
echo ""
echo "🧪 Running tests..."
PYTHONPATH=$PWD python tests/test_orchestrator.py
echo ""

# Offer to start server
echo ""
echo "✅ Setup complete!"
echo ""
echo "Available commands:"
echo "  1. Start server:    uvicorn app.main:app --reload"
echo "  2. Chat (CLI):      python -m app.cli chat user-1 \"Hello\""
echo "  3. Get history:     python -m app.cli history user-1"
echo "  4. Run tests:       PYTHONPATH=\$PWD python tests/test_orchestrator.py"
echo "  5. Docker:          docker-compose up --build"
echo ""

read -p "Would you like to start the server now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🌐 Starting FastAPI server..."
    echo "   Server will be available at: http://127.0.0.1:8000"
    echo "   API docs at: http://127.0.0.1:8000/docs"
    echo "   Press Ctrl+C to stop"
    echo ""
    uvicorn app.main:app --reload
else
    echo ""
    echo "To start the server later, run:"
    echo "  source .venv/bin/activate"
    echo "  uvicorn app.main:app --reload"
fi
