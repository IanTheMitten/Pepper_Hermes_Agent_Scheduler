from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Block:
    id: int
    start: int          # minutes on an abstract daily timeline
    end: int
    min_duration: int
    rigidity: float
    protection: float
    location: str | None
    divisible: bool
    earliest: int       # window start
    latest: int         # window end (deadline cap)
    anchor: bool        # fixed point (max rigidity / fixed-time)

    @property
    def duration(self) -> int:
        return self.end - self.start


def place(block: Block, new_start: int) -> Block:
    """Shift: move to new_start, keep duration."""
    return replace(block, start=new_start, end=new_start + block.duration)


def place_compressed(block: Block, new_start: int, new_duration: int) -> Block:
    """Compress (and place): clamp to the min_duration floor."""
    dur = max(block.min_duration, new_duration)
    return replace(block, start=new_start, end=new_start + dur)


def split_head(block: Block, new_start: int) -> tuple[Block, int]:
    """Divisible split: place min_duration now, return (head, deferred_minutes)."""
    deferred = block.duration - block.min_duration
    head = replace(block, start=new_start, end=new_start + block.min_duration)
    return head, max(0, deferred)
