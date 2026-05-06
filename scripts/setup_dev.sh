#!/usr/bin/env bash
# Development environment setup for SPEC-1
set -euo pipefail

echo "==> Setting up SPEC-1 development environment"

# 1. Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_major=3
required_minor=9
actual_minor=$(echo "$python_version" | cut -d. -f2)
if [ "$actual_minor" -lt "$required_minor" ]; then
    echo "ERROR: Python 3.${required_minor}+ required (found $python_version)"
    exit 1
fi
echo "    Python $python_version — OK"

# 2. Create .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "    Created .env from .env.example"
    echo "    ACTION REQUIRED: set ANTHROPIC_API_KEY in .env"
else
    echo "    .env already exists — skipping"
fi

# 3. Install package + dev deps
echo "==> Installing dependencies"
pip install -e ".[dev]"

# 4. Optionally install quant deps
if [ "${1:-}" = "--quant" ]; then
    echo "==> Installing quant dependencies (numpy, pandas, yfinance)"
    pip install -e ".[quant]"
fi

# 5. Create generated/ directory
mkdir -p generated/briefs generated/reports generated/exports
echo "    Created generated/ directories"

# 6. Smoke test
echo "==> Running smoke test"
PYTHONPATH=src python -c "from spec1_engine.core.engine import IntelligenceEngine; print('    Engine import — OK')"
PYTHONPATH=src python -c "from spec1_api.main import app; print('    API import — OK')"
PYTHONPATH=src python -c "import mcp_server; print('    MCP server import — OK')"

echo ""
echo "Setup complete. Next steps:"
echo "  1. Edit .env and set ANTHROPIC_API_KEY"
echo "  2. make test          # verify full test suite"
echo "  3. make cycle         # run one-shot intelligence cycle"
echo "  4. make run           # start API server at http://localhost:8000"
