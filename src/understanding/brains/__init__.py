"""Brains turn a Turn into a stream of text deltas.

The contract is deliberately tiny so any backend fits: Claude Code headless,
a raw API client, a local model server. A brain owns its conversation state;
`reset()` starts a new conversation, `interrupt()` stops the current answer.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Image:
    data: bytes
    media_type: str
    width: int
    height: int


@dataclass(frozen=True)
class Turn:
    question: str
    images: list[Image] = field(default_factory=list)
    context_notes: list[str] = field(default_factory=list)


class Brain(Protocol):
    def start(self) -> None:
        """Warm up (spawn processes, open connections). Called once, off the main thread."""

    def stream(self, turn: Turn) -> Iterator[str]:
        """Yield text deltas for one answer. Blocks the calling (worker) thread."""

    def interrupt(self) -> None:
        """Stop the in-flight answer, keeping the conversation. Thread-safe."""

    def reset(self) -> None:
        """Forget the conversation."""

    def close(self) -> None: ...


BrainFactory = Callable[..., Brain]
_REGISTRY: dict[str, BrainFactory] = {}


def register(name: str) -> Callable[[BrainFactory], BrainFactory]:
    def deco(factory: BrainFactory) -> BrainFactory:
        _REGISTRY[name] = factory
        return factory

    return deco


def create(name: str, **options) -> Brain:
    # Import built-ins lazily so registering is a side effect of first use.
    from understanding.brains import claude_code, replay  # noqa: F401

    if name not in _REGISTRY:
        raise ValueError(f"unknown brain {name!r}; have {sorted(_REGISTRY)}")
    return _REGISTRY[name](**options)
