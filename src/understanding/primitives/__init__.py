"""Primitives are the plugin unit of the renderer.

A primitive is a pair of files sharing a name:
    <name>.md  — the prompt doc the brain sees (what the op does, its fields, an example line)
    <name>.js  — the renderer handler: U.register("<name>", (op, ctx) => {...})

Built-ins live next to this file. Drop extra pairs into
~/.config/understanding/primitives/ to add or override primitives without
touching the core; list them under `primitives` in config to enable them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BUILTIN_DIR = Path(__file__).parent
USER_DIR = Path.home() / ".config" / "understanding" / "primitives"


@dataclass(frozen=True)
class Primitive:
    name: str
    doc: str
    js: str


def discover(dirs: list[Path] | None = None) -> dict[str, Primitive]:
    """Later dirs override earlier ones, so user primitives shadow built-ins."""
    found: dict[str, Primitive] = {}
    for d in dirs if dirs is not None else [BUILTIN_DIR, USER_DIR]:
        if not d.is_dir():
            continue
        for doc in sorted(d.glob("*.md")):
            js = doc.with_suffix(".js")
            found[doc.stem] = Primitive(
                name=doc.stem,
                doc=doc.read_text().strip(),
                js=js.read_text() if js.exists() else "",
            )
    return found


def select(available: dict[str, Primitive], enabled: list[str] | None) -> list[Primitive]:
    if not enabled:
        return list(available.values())
    missing = [n for n in enabled if n not in available]
    if missing:
        raise ValueError(f"unknown primitives in config: {missing}; have {sorted(available)}")
    return [available[n] for n in enabled]
