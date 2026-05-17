# LLM Fallback Setup — SPEC-1

SPEC-1 runs a three-tier LLM chain so the pipeline never stalls on API budget
or connectivity issues.

```
Tier 1  Claude (Anthropic API)   — primary, ~$0.0003–0.002 / call
Tier 2  Ollama + Llama3/Mistral  — local, free, ~85–90 % parity
Tier 3  Rule-based mock          — deterministic, always available
```

---

## Tier 1 — Anthropic Claude

Already configured. Set your key in `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Fallback triggers on HTTP 401, 429, or any network error.

---

## Tier 2 — Local Ollama (one-time setup)

### Install

```bash
# macOS
brew install ollama

# Linux / WSL
curl -fsSL https://ollama.com/install.sh | sh
```

### Pull the model

```bash
# 8 GB+ RAM  (default)
ollama pull llama3

# Under 8 GB RAM  (auto-selected by SPEC-1)
ollama pull mistral
```

### Start the server

```bash
ollama serve          # listens on localhost:11434
```

SPEC-1 will auto-spawn Ollama if `OLLAMA_AUTO_SPAWN=true` (default) and the
binary is in your `PATH`.  Set `OLLAMA_AUTO_SPAWN=false` to disable.

### Env vars

```env
SPEC1_OLLAMA_URL=http://localhost:11434   # default
OLLAMA_MODEL=llama3                       # override auto-selection
OLLAMA_AUTO_SPAWN=true
```

---

## Tier 3 — Rule-Based Mock

No setup required.  Activates automatically when both Claude and Ollama are
unavailable.  Uses keyword scoring to produce a deterministic verdict:

| Signal type       | Verdict  | SPEC-1 classification |
|-------------------|----------|-----------------------|
| 2+ threat keywords | THREAT  | ESCALATE              |
| 1 threat or 2+ anomaly | ANOMALY | INVESTIGATE       |
| No matches        | CLEAR    | MONITOR               |

Confidence is capped at 0.75 (Tier 3 is conservative by design).

---

## Fallback Log

Every LLM call is appended to `logs/llm_fallback.jsonl`:

```json
{"ts": "2026-05-17T06:00:01Z", "session": "a3f1b2c4", "tier": "claude",
 "latency_ms": 820, "char_count": 312, "success": true}
```

Monitor tier usage with:

```bash
jq '.tier' logs/llm_fallback.jsonl | sort | uniq -c
```

---

## Verify the Chain

```python
from spec1_engine.llm.fallback_client import FallbackLLMClient

llm = FallbackLLMClient()
result = llm.analyze("Armed forces launched a missile strike.", system="")
print(result)
# {'verdict': 'THREAT', 'confidence': 0.55, 'analysis': '...', 'tier_used': 'claude', ...}

print(llm.get_active_tier())   # 'claude' | 'ollama' | 'mock'
print(llm.get_cost_estimate()) # cumulative USD this session
```
