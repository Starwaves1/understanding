"""Config: built-in defaults, overridden by ~/.config/understanding/config.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PATH = Path.home() / ".config" / "understanding" / "config.toml"


@dataclass
class Config:
    brain: str = "claude_code"
    # Passed to the brain factory, e.g. model, tools, extra_args.
    brain_options: dict[str, Any] = field(default_factory=lambda: {"model": "haiku"})
    context: list[str] = field(default_factory=lambda: ["screen", "frontmost_app"])
    context_options: dict[str, dict] = field(default_factory=dict)
    # Empty = every discovered primitive.
    primitives: list[str] = field(default_factory=list)
    # Appended to the system prompt: house style, persona, extra rules.
    prompt_extra: str = ""
    # Modifiers that, tapped together and released alone, open the prompt box.
    hotkey: list[str] = field(default_factory=lambda: ["control", "option"])
    tap_max_seconds: float = 0.5


def load(path: Path = PATH) -> Config:
    cfg = Config()
    if not path.exists():
        return cfg
    data = tomllib.loads(path.read_text())
    for key, value in data.items():
        if not hasattr(cfg, key):
            raise ValueError(f"{path}: unknown key {key!r}")
        if key.endswith("_options"):
            getattr(cfg, key).update(value)
        else:
            setattr(cfg, key, value)
    return cfg
