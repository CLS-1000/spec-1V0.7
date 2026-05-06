#!/usr/bin/env bash
# Run a SPEC-1 intelligence cycle with optional flags
set -euo pipefail

PYTHONPATH=src
export PYTHONPATH

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --quant       Enable quantitative market pipeline"
    echo "  --dry-run     Parse and score signals; skip investigation and briefing"
    echo "  --brief-only  Generate brief from existing records (no new cycle)"
    echo "  --help        Show this message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Standard cycle"
    echo "  $0 --quant            # Cycle with market signals"
    echo "  $0 --brief-only       # Regenerate brief from last cycle's records"
}

QUANT=false
DRY_RUN=false
BRIEF_ONLY=false

for arg in "$@"; do
    case $arg in
        --quant)      QUANT=true ;;
        --dry-run)    DRY_RUN=true ;;
        --brief-only) BRIEF_ONLY=true ;;
        --help)       usage; exit 0 ;;
        *)            echo "Unknown option: $arg"; usage; exit 1 ;;
    esac
done

if [ "$BRIEF_ONLY" = true ]; then
    echo "==> Generating brief from existing records"
    python -m spec1_engine.tools.historical_briefs
    exit 0
fi

if [ "$QUANT" = true ]; then
    export SPEC1_QUANT_ENABLED=true
fi

echo "==> Starting SPEC-1 cycle ($(date -u '+%Y-%m-%dT%H:%M:%SZ'))"
echo "    Quant: $QUANT | Dry-run: $DRY_RUN"

if [ "$DRY_RUN" = true ]; then
    python -c "
import asyncio
from spec1_engine.signal.harvester import Harvester
from spec1_engine.signal.parser import Parser
from spec1_engine.signal.scorer import Scorer

h = Harvester()
p = Parser()
s = Scorer()

signals = h.harvest()
print(f'Harvested: {len(signals)} signals')
parsed = [p.parse(sig) for sig in signals]
opps = [o for ps in parsed for o in [s.score(ps)] if o]
print(f'Opportunities: {len(opps)} passed all 4 gates')
"
else
    python -m spec1_engine.app.cycle
fi

echo "==> Cycle complete ($(date -u '+%Y-%m-%dT%H:%M:%SZ'))"
