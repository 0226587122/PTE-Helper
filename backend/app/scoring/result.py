from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ScoreResult:
    score: float
    max_score: float
    detail: dict[str, Any] = field(default_factory=dict)
    zeroed_reason: str | None = None

    @property
    def pct(self) -> float:
        if self.max_score <= 0:
            return 0.0
        return round(max(0.0, min(1.0, self.score / self.max_score)) * 100, 1)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["pct"] = self.pct
        return data


def estimated_score(average_pct: float) -> int:
    """Map an average percentage onto the 10 to 90 PTE scale. A practice estimate only."""
    return int(round(10 + 80 * max(0.0, min(100.0, average_pct)) / 100))
