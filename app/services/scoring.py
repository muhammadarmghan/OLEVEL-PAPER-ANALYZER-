"""Topic likelihood scoring and rolling-origin backtesting (pure Python, no database)."""
import math
from dataclasses import dataclass
from itertools import product

DEFAULT_WEIGHTS = {"recency_frequency": 0.40, "mark_weight": 0.30, "overdue": 0.15, "coverage_balance": 0.15}
DECAY, WINDOW = 0.8, 4


@dataclass
class Scored:
    topic_id: int
    score: float
    signals: dict
    tier: str = "lower"
    rank: int = 0


def compute_signals(appeared, mark_share, decay=DECAY, window=WINDOW):
    """appeared / mark_share are lists ordered oldest -> newest (one entry per session)."""
    n = len(appeared)
    w = [decay ** (n - 1 - i) for i in range(n)]
    total = sum(w)
    rf = sum(wi * a for wi, a in zip(w, appeared)) / total
    mw = sum(wi * m for wi, m in zip(w, mark_share)) / total
    seen = [i for i, a in enumerate(appeared) if a]
    if seen:
        since_last = n - 1 - seen[-1]
        gaps = [b - a for a, b in zip(seen, seen[1:])]
        typical_gap = sum(gaps) / len(gaps) if gaps else float(n)
        overdue = min(1.0, since_last / max(typical_gap, 1.0))
    else:
        since_last, overdue = n, 0.5          # never seen: unknown, neutral value
    recent = appeared[-window:]
    coverage = 1.0 - sum(recent) / len(recent)
    return {"recency_frequency": rf, "mark_weight": mw, "overdue": overdue,
            "coverage_balance": coverage, "sessions_since_last": since_last,
            "appearances": sum(appeared)}


def score_topics(history, weights=None):
    """history = {topic_id: (appeared_list, share_list)} -> list[Scored] sorted best first."""
    weights = weights or DEFAULT_WEIGHTS
    sig = {tid: compute_signals(a, s) for tid, (a, s) in history.items()}
    top_mw = max((v["mark_weight"] for v in sig.values()), default=0) or 1.0
    scored = []
    for tid, v in sig.items():
        v = dict(v, mark_weight=v["mark_weight"] / top_mw)
        scored.append(Scored(tid, sum(weights[k] * v[k] for k in weights), v))
    scored.sort(key=lambda s: (-s.score, s.topic_id))
    n = len(scored)
    very, likely = math.ceil(n * 0.20), math.ceil(n * 0.50)
    for rank, s in enumerate(scored, start=1):
        s.rank = rank
        s.tier = "very_likely" if rank <= very else "likely" if rank <= likely else "lower"
    return scored


def explain(s: Scored, total_sessions: int) -> list[dict]:
    """One human-readable reason per signal (stored in prediction_reasons)."""
    v = s.signals
    return [
        {"signal": "recency_frequency", "value": v["recency_frequency"],
         "explanation": f"Appeared in {v['appearances']} of {total_sessions} sessions (recent sessions count more)."},
        {"signal": "mark_weight", "value": v["mark_weight"],
         "explanation": "Carries a high share of paper marks compared with other topics."},
        {"signal": "overdue", "value": v["overdue"],
         "explanation": f"Last seen {v['sessions_since_last']} session(s) ago compared with its usual gap."},
        {"signal": "coverage_balance", "value": v["coverage_balance"],
         "explanation": "Under-represented in the last few sessions."},
    ]


def backtest(history, k=5, min_history=4, weights=None):
    """Rolling origin: predict each session from the sessions before it."""
    n_sessions = len(next(iter(history.values()))[0])
    rows = []
    for t in range(min_history, n_sessions):
        past = {tid: (a[:t], s[:t]) for tid, (a, s) in history.items()}
        top = [x.topic_id for x in score_topics(past, weights)[:k]]
        base = sorted(history, key=lambda tid: (-sum(history[tid][0][:t]), tid))[:k]
        actual = {tid for tid, (a, _) in history.items() if a[t]}
        total_share = sum(s[t] for _, s in history.values()) or 1.0
        rows.append({
            "session_index": t,
            "hit_rate": len(set(top) & actual) / k,
            "mark_coverage": sum(history[tid][1][t] for tid in top) / total_share,
            "baseline_hit_rate": len(set(base) & actual) / k,
            "baseline_mark_coverage": sum(history[tid][1][t] for tid in base) / total_share,
        })
    return rows


def tune_weights(history, k=5, step=0.05, train_until=None):
    """Grid-search weights that sum to 1; optimise mean mark coverage on the training sessions."""
    keys, steps = list(DEFAULT_WEIGHTS), round(1 / step)
    best, best_score = DEFAULT_WEIGHTS, -1.0
    for combo in product(range(steps + 1), repeat=len(keys) - 1):
        if sum(combo) > steps:
            continue
        values = [c * step for c in combo] + [1 - sum(combo) * step]
        weights = dict(zip(keys, values))
        rows = backtest(history, k=k, weights=weights)
        if train_until is not None:
            rows = [r for r in rows if r["session_index"] < train_until]
        score = sum(r["mark_coverage"] for r in rows) / len(rows)
        if score > best_score:
            best, best_score = weights, score
    return best, best_score
