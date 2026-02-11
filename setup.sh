#!/bin/bash

# Setup script for Loan Collateral Check AI Agent System
# This script initializes the project environment

set -e  # Exit on error

echo "==================================="
echo "Loan Collateral Check - Setup"
echo "==================================="
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

echo "✓ Dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.template .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys:"
    echo "   - GEMINI_API_KEY"
    echo "   - SERP_API_KEY (optional)"
    echo ""
else
    echo "✓ .env file already exists"
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p data/chromadb
mkdir -p database
mkdir -p logs
mkdir -p langflow_flows/components
echo "✓ Directories created"

# Initialize database
echo "Initializing database..."
python database/init_db.py
echo "✓ Database initialized"

# Check if API keys are configured
if grep -q "your_gemini_api_key_here" .env; then
    echo ""
    echo "⚠️  WARNING: GEMINI_API_KEY not configured in .env"
    echo "   Please update .env with your actual API key"
    echo ""
fi

echo ""
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Run LangFlow: langflow run --host 0.0.0.0 --port 7860"
echo "4. Open browser: http://localhost:7860"
echo "5. Import flow: langflow_flows/main_orchestrator.json"
echo ""
echo "For Docker deployment:"
echo "  docker-compose -f docker-compose.new.yml up --build"
echo ""
