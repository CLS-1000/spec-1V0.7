# @domain:   intelligence
# @module:   adapters_quant
# @loc:      gh_main
# @status:   stable
# @depends:  cls_db, spec1_core

"""Quantitative market intelligence adapter.

Watches defense, cyber, energy, and macro tickers as a corroborating signal
layer alongside OSINT feeds. A stock breakout in LMT on the same day as a
FARA filing or Congressional vote is a stronger combined signal than either alone.

Uses yfinance when available; falls back to deterministic synthetic data.
Passes signals through a 4-gate filter (credibility, volume, velocity, novelty)
before emitting OSINTRecord objects.
"""

from __future__ import annotations

import hashlib
import importlib.util
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from cls_osint.schemas import OSINTRecord

logger = logging.getLogger("spec1.osint.quant")

_YFINANCE_AVAILABLE = importlib.util.find_spec("yfinance") is not None

# ── Watchlist ──────────────────────────────────────────────────────────────────

@dataclass
class _TickerMeta:
    ticker: str
    name: str
    sector: str
    tags: list[str] = field(default_factory=list)
    credibility: float = 0.8


_WATCHLIST: dict[str, _TickerMeta] = {
    # Defense & Aerospace
    "LMT": _TickerMeta("LMT", "Lockheed Martin",            "defense", ["missiles", "aircraft"]),
    "RTX": _TickerMeta("RTX", "RTX / Raytheon",             "defense", ["missiles", "sensors"]),
    "NOC": _TickerMeta("NOC", "Northrop Grumman",           "defense", ["cyber", "space"]),
    "GD":  _TickerMeta("GD",  "General Dynamics",           "defense", ["submarines"]),
    "BA":  _TickerMeta("BA",  "Boeing",                     "aerospace", ["aircraft"]),
    "HII": _TickerMeta("HII", "Huntington Ingalls",         "defense", ["ships", "nuclear"]),
    "L3H": _TickerMeta("L3H", "L3Harris",                   "defense", ["comms", "intel"]),
    "LDOS":_TickerMeta("LDOS","Leidos",                     "defense", ["IT", "intelligence"]),
    # Cyber
    "CRWD":_TickerMeta("CRWD","CrowdStrike",                "cyber",   ["EDR", "threat intel"], 0.9),
    "PANW":_TickerMeta("PANW","Palo Alto Networks",         "cyber",   ["NGFW", "cloud"],       0.9),
    "FTNT":_TickerMeta("FTNT","Fortinet",                   "cyber",   ["network security"],    0.85),
    "ZS":  _TickerMeta("ZS",  "Zscaler",                   "cyber",   ["zero trust"],           0.85),
    # Energy / Critical Infrastructure
    "XOM": _TickerMeta("XOM", "ExxonMobil",                 "energy",  ["oil", "gas"],           0.85),
    "NEE": _TickerMeta("NEE", "NextEra Energy",             "energy",  ["nuclear", "renewables"],0.8),
    # Macro
    "SPY": _TickerMeta("SPY", "S&P 500 ETF",               "macro",   ["broad market"],          0.95),
    "TLT": _TickerMeta("TLT", "20yr Treasury ETF",         "macro",   ["bonds", "rates"],        0.95),
    "GLD": _TickerMeta("GLD", "SPDR Gold",                 "macro",   ["gold", "safe haven"],    0.95),
    "USO": _TickerMeta("USO", "US Oil Fund",               "macro",   ["oil", "commodity"],      0.85),
}

# ── OHLCV bar ─────────────────────────────────────────────────────────────────

@dataclass
class _Bar:
    ticker: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def daily_return(self) -> float:
        if self.open == 0:
            return 0.0
        return round((self.close - self.open) / self.open, 6)


# ── Data collection ───────────────────────────────────────────────────────────

def _synthetic_bars(ticker: str, days: int = 30) -> list[_Bar]:
    random.seed(hash(ticker) % 10_000)
    base = 100.0 + (hash(ticker) % 400)
    bars: list[_Bar] = []
    today = datetime.now(timezone.utc).date()
    for i in range(days, 0, -1):
        date = today - timedelta(days=i)
        if date.weekday() >= 5:
            continue
        change = (random.random() - 0.48) * 0.04
        open_ = round(base, 2)
        close = round(base * (1 + change), 2)
        high  = round(max(open_, close) * (1 + random.random() * 0.02), 2)
        low   = round(min(open_, close) * (1 - random.random() * 0.02), 2)
        vol   = float(random.randint(500_000, 20_000_000))
        bars.append(_Bar(ticker, date.isoformat(), open_, high, low, close, vol))
        base = close
    return bars


def _fetch_yfinance(ticker: str, period: str = "1mo") -> list[_Bar]:
    import yfinance as yf  # type: ignore[import]
    hist = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    bars: list[_Bar] = []
    for idx, row in hist.iterrows():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
        bars.append(_Bar(
            ticker=ticker,
            date=date_str,
            open=float(row.get("Open", 0)),
            high=float(row.get("High", 0)),
            low=float(row.get("Low", 0)),
            close=float(row.get("Close", 0)),
            volume=float(row.get("Volume", 0)),
        ))
    return bars


def _fetch(ticker: str, use_synthetic: bool = False) -> list[_Bar]:
    if use_synthetic or not _YFINANCE_AVAILABLE:
        return _synthetic_bars(ticker)
    try:
        bars = _fetch_yfinance(ticker)
        if bars:
            return bars
    except Exception as exc:
        logger.debug("yfinance fetch failed for %s: %s", ticker, exc)
    return _synthetic_bars(ticker)


# ── Indicators ────────────────────────────────────────────────────────────────

def _rsi(bars: list[_Bar], period: int = 14) -> float:
    closes = [b.close for b in bars]
    if len(closes) < period + 1:
        return float("nan")
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(d if d >= 0 else 0.0)
        losses.append(abs(d) if d < 0 else 0.0)
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_g / avg_l)), 2)


def _relative_volume(bars: list[_Bar], lookback: int = 20) -> float:
    if len(bars) < 2:
        return 1.0
    prior = bars[:-1][-lookback:]
    avg = sum(b.volume for b in prior) / len(prior) if prior else 0
    return round(bars[-1].volume / avg, 3) if avg else 1.0


# ── 4-gate scorer ─────────────────────────────────────────────────────────────

_CREDIBILITY_MIN  = 0.6
_REL_VOL_MIN      = 1.2
_VELOCITY_MIN     = 0.015
_RSI_NEUTRAL_LOW  = 40
_RSI_NEUTRAL_HIGH = 60


def _detect_pattern(bar: _Bar, rel_vol: float, rsi_val: float) -> str:
    if bar.daily_return >= 0.03 and rel_vol >= 1.5:
        return "HIGH_VOL_BREAKOUT"
    if bar.daily_return <= -0.03 and rel_vol >= 1.5:
        return "HIGH_VOL_BREAKDOWN"
    if not math.isnan(rsi_val):
        if rsi_val > 70:
            return "OVERBOUGHT"
        if rsi_val < 30:
            return "OVERSOLD"
    if bar.daily_return > 0:
        return "MOMENTUM_UP"
    if bar.daily_return < 0:
        return "MOMENTUM_DOWN"
    return "NEUTRAL"


def _score(ticker: str, bars: list[_Bar]) -> Optional[dict]:
    """Run 4-gate filter; return signal dict if all gates pass, else None."""
    if not bars:
        return None
    meta = _WATCHLIST.get(ticker)
    if not meta:
        return None

    bar     = bars[-1]
    rsi_val = _rsi(bars)
    rel_vol = _relative_volume(bars)

    gates = {
        "credibility": meta.credibility >= _CREDIBILITY_MIN,
        "volume":      rel_vol >= _REL_VOL_MIN,
        "velocity":    abs(bar.daily_return) >= _VELOCITY_MIN,
        "novelty":     math.isnan(rsi_val) or rsi_val < _RSI_NEUTRAL_LOW or rsi_val > _RSI_NEUTRAL_HIGH,
    }
    if not all(gates.values()):
        return None

    pattern = _detect_pattern(bar, rel_vol, rsi_val)
    return {
        "ticker":       ticker,
        "sector":       meta.sector,
        "name":         meta.name,
        "tags":         meta.tags,
        "pattern":      pattern,
        "date":         bar.date,
        "daily_return": bar.daily_return,
        "rel_volume":   rel_vol,
        "rsi":          rsi_val,
        "close":        bar.close,
        "volume":       int(bar.volume),
        "gates":        gates,
    }


# ── OSINTRecord builder ───────────────────────────────────────────────────────

def _make_record_id(ticker: str, pattern: str, date: str) -> str:
    raw = f"{ticker}::{pattern}::{date}"
    return "qsig_" + hashlib.sha256(raw.encode()).hexdigest()[:12]


def _to_osint_record(sig: dict) -> OSINTRecord:
    ticker  = sig["ticker"]
    pattern = sig["pattern"]
    sector  = sig["sector"]
    ret_pct = sig["daily_return"] * 100
    content = (
        f"{ticker} ({sig['name']}) — {pattern} | "
        f"ret={ret_pct:+.2f}% rel_vol={sig['rel_volume']:.2f}x "
        f"RSI={sig['rsi'] if not math.isnan(sig['rsi']) else 'n/a'} | "
        f"sector={sector} | {sig['date']}"
    )
    return OSINTRecord(
        record_id=_make_record_id(ticker, pattern, sig["date"]),
        source_type="MARKET",
        source_name="quant_adapter",
        content=content,
        url=f"https://finance.yahoo.com/quote/{ticker}",
        collected_at=datetime.now(timezone.utc),
        metadata={k: v for k, v in sig.items() if k != "gates"},
    )


# ── Public adapter interface ──────────────────────────────────────────────────

def get_signals(use_synthetic: bool = False) -> list[OSINTRecord]:
    """Fetch market data for all watchlist tickers and return scored signals."""
    records: list[OSINTRecord] = []
    for ticker in _WATCHLIST:
        try:
            bars = _fetch(ticker, use_synthetic=use_synthetic)
            sig  = _score(ticker, bars)
            if sig:
                records.append(_to_osint_record(sig))
        except Exception as exc:
            logger.debug("quant adapter error for %s: %s", ticker, exc)
    logger.info("quant adapter: %d signals from %d tickers", len(records), len(_WATCHLIST))
    return records


class QuantAdapter:
    """OSINT adapter wrapping the quant market-intelligence pipeline."""

    def get_signals(self, use_synthetic: bool = False) -> list[OSINTRecord]:
        return get_signals(use_synthetic=use_synthetic)
