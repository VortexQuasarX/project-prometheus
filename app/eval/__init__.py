"""Evaluation harness (app/eval).

- :mod:`app.eval.judge`    — rule-based 8-metric scoring of a chat response
                             against a golden case (SPEC "EVALUATION HARNESS
                             REQUIREMENTS").
- :mod:`app.eval.runner`   — in-process golden-set runner over the chat
                             service layer (DECISIONS B17 / subagent_01 D10),
                             persisting ``eval_runs`` / ``eval_results``.
- :mod:`app.eval.metrics`  — average-metrics aggregation for eval runs.

The golden prompt catalogue lives in ``evals/golden_prompts.yaml`` (repo
root), not under ``app/`` — the runner resolves it via
``Path(__file__).resolve().parents[2] / "evals"``.
"""

from __future__ import annotations

from app.eval.metrics import average_metrics

__all__ = ["average_metrics"]
