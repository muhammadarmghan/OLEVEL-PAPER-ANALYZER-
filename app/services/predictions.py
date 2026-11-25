"""Create a PredictionRun: statistics -> scores -> tiers -> reasons -> backtest."""
from ..extensions import db
from ..models import BacktestResult, Prediction, PredictionReason, PredictionRun
from .aggregation import build_history, recompute_topic_stats
from .scoring import DEFAULT_WEIGHTS, backtest, explain, score_topics

MIN_SESSIONS = 5  # 4 sessions of history are needed before the first backtest target


def run_prediction(subject_id: int, user_id=None, weights=None, k: int = 5) -> PredictionRun:
    recompute_topic_stats(subject_id)
    history = build_history(subject_id)
    n = len(history.sessions)
    if n < MIN_SESSIONS:
        raise ValueError(f"Need approved questions from at least {MIN_SESSIONS} exam sessions (found {n}).")
    weights = weights or DEFAULT_WEIGHTS
    scoring_history = history.for_scoring()

    run = PredictionRun(subject_id=subject_id, created_by=user_id, algorithm_version="v1",
                        weights=weights, trained_through_year=history.sessions[-1].year)
    for s in score_topics(scoring_history, weights):
        prediction = Prediction(topic_id=s.topic_id, score=s.score, rank=s.rank, tier=s.tier)
        prediction.reasons = [PredictionReason(**r) for r in explain(s, n)]
        run.predictions.append(prediction)
    k = min(k, len(history.topic_ids))
    for row in backtest(scoring_history, k=k, weights=weights):
        run.backtests.append(BacktestResult(
            target_session_id=history.sessions[row["session_index"]].id, k=k, hit_rate=row["hit_rate"],
            mark_coverage=row["mark_coverage"], baseline_hit_rate=row["baseline_hit_rate"]))
    db.session.add(run)
    db.session.commit()
    return run
