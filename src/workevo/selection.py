"""Paired promotion, normalized objectives and bounded Pareto selection."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from .contracts import Policy, Summary


def compare(candidate: Summary, incumbent: Summary | None, policy: Policy) -> dict[str, str]:
    if candidate.split != "validation" or not candidate.eligible:
        return {"outcome": "inconclusive", "reason": "incomplete or ineligible validation evidence"}
    if candidate.quality < policy.quality_floor:
        return {"outcome": "rejected", "reason": "quality floor not met"}
    if incumbent is None:
        return {"outcome": "accepted", "reason": "eligible seed"}
    if (
        not incumbent.eligible
        or candidate.identity != incumbent.identity
        or candidate.expected_keys != incumbent.expected_keys
        or incumbent.split != candidate.split
    ):
        return {"outcome": "inconclusive", "reason": "incompatible paired evidence"}
    previous = {f"{e.case_id}:{e.repeat}": e.correct for e in incumbent.evaluations}
    if any(previous[f"{e.case_id}:{e.repeat}"] and not e.correct for e in candidate.evaluations):
        return {"outcome": "rejected", "reason": "per-case correctness regression"}
    gain = candidate.quality - incumbent.quality
    if gain > 0 and gain >= policy.min_gain:
        return {"outcome": "accepted", "reason": "paired correctness improved"}
    if gain == 0 and candidate.calls < incumbent.calls:
        return {"outcome": "accepted", "reason": "equal correctness with fewer operator calls"}
    return {"outcome": "rejected", "reason": "no qualifying improvement"}


@dataclass(frozen=True)
class FrontierPoint:
    summary: Summary
    family: str
    micro_usd: float | None = None


def frontier(
    points: list[FrontierPoint], *, cap: int = 16, epsilon: float = 0, require_cost: bool = False
) -> list[FrontierPoint]:
    if cap < 1 or not math.isfinite(epsilon) or epsilon < 0:
        raise ValueError("invalid frontier bounds")
    valid = [
        p for p in points if p.summary.eligible and (not require_cost or p.micro_usd is not None)
    ]
    if not valid:
        return []
    if (
        len(
            {
                (p.summary.identity, p.summary.split, p.summary.expected_keys, p.family)
                for p in valid
            }
        )
        != 1
    ):
        raise ValueError("frontier evidence is not comparable")

    def coordinates(p: FrontierPoint) -> tuple[float, ...]:
        values: tuple[float, ...] = (p.summary.quality, -p.summary.calls, -p.summary.latency_ms)
        if require_cost:
            if p.micro_usd is None or not math.isfinite(p.micro_usd) or p.micro_usd < 0:
                raise ValueError("invalid monetary metric")
            values += (-p.micro_usd,)
        return tuple(math.floor(v / epsilon) if epsilon else v for v in values)

    ordered = sorted(
        {p.summary.revision: p for p in valid}.values(),
        key=lambda p: (-p.summary.quality, p.summary.calls, p.summary.revision),
    )
    result: list[FrontierPoint] = []
    for point in ordered:
        current = coordinates(point)
        if not any(
            all(a >= b for a, b in zip(coordinates(other), current, strict=True))
            and any(a > b for a, b in zip(coordinates(other), current, strict=True))
            for other in ordered
            if other is not point
        ) and not any(coordinates(existing) == current for existing in result):
            result.append(point)
    return result[:cap]


def route(
    points: list[FrontierPoint],
    family: str,
    *,
    priority: Literal["quality", "calls", "latency", "cost"] = "quality",
    min_quality: float = 0,
    max_calls: float | None = None,
) -> FrontierPoint | None:
    valid = [
        p
        for p in points
        if p.family == family
        and p.summary.eligible
        and p.summary.quality >= min_quality
        and (max_calls is None or p.summary.calls <= max_calls)
    ]
    if len({p.summary.identity for p in valid}) > 1:
        raise ValueError("routing requires one comparison identity per task family")
    if priority == "cost":
        valid = [p for p in valid if p.micro_usd is not None]
    if not valid:
        return None

    def key(p: FrontierPoint) -> tuple[float, str]:
        value = {
            "quality": -p.summary.quality,
            "calls": p.summary.calls,
            "latency": p.summary.latency_ms,
            "cost": p.micro_usd or 0,
        }[priority]
        return value, p.summary.revision

    return min(valid, key=key)
