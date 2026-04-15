#!/bin/bash
# Final Sprint 3 bench run — execute once OpenAI credits are available.
# 5 approaches × 2 models × 41 questions = 410 cells
# Estimated time: 25-35 min

set -e

echo "=== Step 1: Rebuild community index (gpt-4o-mini summaries) ==="
python -c "
import sys; sys.path.insert(0, '.')
from llm_rag.community_service import build_community_index
r = build_community_index('gpt-4o-mini', force_rebuild=True)
print('Community index:', r)
"

echo ""
echo "=== Step 2: Full bench run (410 cells) ==="
time python -m bench.run_eval \
    --approach b1_sql,b2_rag_cypher,b2_rag_community,b2_rag_hybrid,b3_aqr \
    --model gpt-4o-mini,gpt-4o \
    --level all \
    --run-id sprint3_final

echo ""
echo "=== Step 3: AQR classifier self-test ==="
python -m llm_aqr.router

echo ""
echo "=== Done! Results at bench/results/sprint3_final/ ==="
echo "Next: analyze with python and update thesis."
