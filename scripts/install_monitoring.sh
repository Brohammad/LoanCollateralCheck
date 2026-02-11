#!/bin/bash
# Install monitoring dependencies

echo "Installing monitoring dependencies..."

pip install prometheus-client structlog opentelemetry-api opentelemetry-sdk opentelemetry-exporter-jaeger psutil httpx fastapi

echo "✓ Dependencies installed"
echo ""
echo "Testing imports..."
python -c "import sys; sys.path.insert(0, '.'); from monitoring import health; print('✓ Health module OK')"
python -c "import sys; sys.path.insert(0, '.'); from monitoring import metrics; print('✓ Metrics module OK')"
python -c "import sys; sys.path.insert(0, '.'); from monitoring import logging; print('✓ Logging module OK')"

echo ""
echo "✅ Monitoring system ready!"
echo ""
echo "Next steps:"
echo "1. See docs/monitoring_guide.md for integration guide"
echo "2. Run: python tests/test_monitoring.py (after installing all deps)"
echo "3. Start your FastAPI app with monitoring enabled"
