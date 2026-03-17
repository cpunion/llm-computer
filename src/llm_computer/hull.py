"""Two-dimensional support-point caches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


Point = tuple[float, float]


def cross(origin: Point, a: Point, b: Point) -> float:
    return (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0])


def convex_hull(points: Iterable[Point]) -> list[Point]:
    unique = sorted(set(points))
    if len(unique) <= 1:
        return list(unique)

    lower: list[Point] = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)

    upper: list[Point] = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)

    return lower[:-1] + upper[:-1]


def support_point(hull: list[Point], query: Point) -> tuple[Point, float]:
    if not hull:
        raise ValueError("Hull must be non-empty")
    if len(hull) == 1:
        point = hull[0]
        return point, query[0] * point[0] + query[1] * point[1]

    lo, hi = 0, len(hull) - 1
    while hi - lo > 2:
        m1 = lo + (hi - lo) // 3
        m2 = hi - (hi - lo) // 3
        s1 = query[0] * hull[m1][0] + query[1] * hull[m1][1]
        s2 = query[0] * hull[m2][0] + query[1] * hull[m2][1]
        if s1 < s2:
            lo = m1 + 1
        else:
            hi = m2 - 1

    best = max(hull[lo:hi + 1], key=lambda point: query[0] * point[0] + query[1] * point[1])
    score = query[0] * best[0] + query[1] * best[1]
    return best, score


class StaticHullCache:
    """Static cache for support-point lookup over a fixed set of keys."""

    def __init__(self) -> None:
        self._value_by_key: dict[Point, float] = {}
        self._hull: list[Point] = []
        self._dirty = False

    def insert(self, key: Point, value: float) -> None:
        self._value_by_key.setdefault(key, value)
        self._dirty = True

    def _ensure_hull(self) -> None:
        if self._dirty:
            self._hull = convex_hull(self._value_by_key)
            self._dirty = False

    def query(self, query: Point) -> float:
        if not self._value_by_key:
            return 0.0
        self._ensure_hull()
        point, _ = support_point(self._hull, query)
        return self._value_by_key[point]


class NaiveCache:
    """Linear-scan baseline."""

    def __init__(self) -> None:
        self._items: list[tuple[Point, float]] = []

    def insert(self, key: Point, value: float) -> None:
        self._items.append((key, value))

    def query(self, query: Point) -> float:
        if not self._items:
            return 0.0
        best_score = float("-inf")
        best_value = 0.0
        for key, value in self._items:
            score = query[0] * key[0] + query[1] * key[1]
            if score > best_score:
                best_score = score
                best_value = value
        return best_value


@dataclass(slots=True)
class HullBlock:
    size: int
    value_by_key: dict[Point, float]
    hull: list[Point]


class OnlineHullCache:
    """Log-structured append-only cache for query+insert workloads."""

    def __init__(self) -> None:
        self.blocks: list[HullBlock] = []

    def _merge(self, older: HullBlock, newer: HullBlock) -> HullBlock:
        value_by_key = dict(older.value_by_key)
        for key, value in newer.value_by_key.items():
            value_by_key.setdefault(key, value)
        return HullBlock(
            size=older.size + newer.size,
            value_by_key=value_by_key,
            hull=convex_hull(value_by_key),
        )

    def insert(self, key: Point, value: float) -> None:
        self.blocks.append(HullBlock(size=1, value_by_key={key: value}, hull=[key]))
        while len(self.blocks) >= 2 and self.blocks[-1].size == self.blocks[-2].size:
            newer = self.blocks.pop()
            older = self.blocks.pop()
            self.blocks.append(self._merge(older, newer))

    def query(self, query: Point) -> float:
        best_score = float("-inf")
        best_value = 0.0
        for block in self.blocks:
            point, score = support_point(block.hull, query)
            if score > best_score:
                best_score = score
                best_value = block.value_by_key[point]
        return best_value
