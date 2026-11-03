"""understanding [run|ask|demo|prompt]"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from understanding import config

LOG = Path.home() / "Library" / "Logs" / "understanding.log"


def _logging(verbose: bool) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr), logging.FileHandler(LOG)],
    )


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="understanding", description="Real-time on-screen explanations.")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--model", help="override brain model (e.g. haiku, sonnet, opus)")
    sub = ap.add_subparsers(dest="cmd")
    run_p = sub.add_parser("run", help="start the menu-bar app (default)")
    run_p.add_argument("--ask", help="ask this immediately on launch (for testing)")
    ask_p = sub.add_parser("ask", help="headless: ask about the current screen, print ops as they stream")
    ask_p.add_argument("question")
    ask_p.add_argument("--no-screen", action="store_true")
    ask_p.add_argument("--image", help="use this image file instead of a live screenshot")
    demo_p = sub.add_parser("demo", help="run the app with a canned answer (no model)")
    demo_p.add_argument("--file", help="JSONL ops file to replay")
    sub.add_parser("prompt", help="print the composed system prompt")
    snap_p = sub.add_parser("snapshot", help="render ops over an image into a standalone HTML file")
    snap_p.add_argument("ops", help="JSONL ops file ('-' for stdin; `ask` output lines also work)")
    snap_p.add_argument("--image", help="background screenshot the ops refer to")
    snap_p.add_argument("--out", default="snapshot.html")
    args = ap.parse_args(argv)
    _logging(args.verbose)

    cfg = config.load()
    if args.model:
        cfg.brain_options["model"] = args.model

    if args.cmd in (None, "run"):
        from understanding.app import run

        run(cfg, auto_ask=getattr(args, "ask", None))
    elif args.cmd == "demo":
        from understanding.app import run

        cfg.brain = "replay"
        cfg.brain_options = {"path": args.file} if args.file else {}
        cfg.context = []
        run(cfg, auto_ask="demo")
    elif args.cmd == "prompt":
        print(_system_prompt(cfg))
    elif args.cmd == "ask":
        _ask(cfg, args)
    elif args.cmd == "snapshot":
        _snapshot(cfg, args)


def _system_prompt(cfg: config.Config) -> str:
    from understanding import primitives, prompt

    return prompt.compose(primitives.select(primitives.discover(), cfg.primitives), cfg.prompt_extra)


def _ask(cfg: config.Config, args: argparse.Namespace) -> None:
    from understanding import brains, context
    from understanding.brains import Image
    from understanding.session import Session

    class PrintRenderer:
        def __init__(self) -> None:
            self.t0 = time.monotonic()

        def begin(self, question, frame):
            print(f"# {question!r} frame={frame}", file=sys.stderr)

        def apply(self, op):
            print(f"{time.monotonic() - self.t0:5.2f}s {json.dumps(op)}", flush=True)

        def end(self, error):
            print(f"# done {time.monotonic() - self.t0:.2f}s" + (f" ERROR {error}" if error else ""), file=sys.stderr)
            done.set()

    import threading

    done = threading.Event()
    if args.image:
        p = Path(args.image)
        import subprocess

        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(p)], capture_output=True, text=True).stdout
        w, h = int(out.split("pixelWidth:")[1].split()[0]), int(out.split("pixelHeight:")[1].split()[0])
        mt = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
        providers = [lambda: context.Contribution(images=[Image(p.read_bytes(), mt, w, h)])]
    elif args.no_screen:
        providers = []
    else:
        providers = context.build(cfg.context, cfg.context_options)

    brain = brains.create(cfg.brain, system_prompt=_system_prompt(cfg), **cfg.brain_options)
    renderer = PrintRenderer()
    session = Session(brain, providers, renderer)
    session.start()
    session.submit(args.question)
    done.wait()
    brain.close()


def _snapshot(cfg: config.Config, args: argparse.Namespace) -> None:
    """Static render for iterating on primitives without the live overlay."""
    import base64
    import subprocess

    from understanding import primitives
    from understanding.protocol import parse_line
    from understanding.ui.overlay import build_html

    text = sys.stdin.read() if args.ops == "-" else Path(args.ops).read_text()
    # Accept raw JSONL or `ask` output ("  1.23s {...}").
    ops = [op for line in text.splitlines() if "{" in line and (op := parse_line(line[line.find("{") :]))]
    w, h, bg = 1280, 800, ""
    if args.image:
        p = Path(args.image)
        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(p)], capture_output=True, text=True).stdout
        w, h = int(out.split("pixelWidth:")[1].split()[0]), int(out.split("pixelHeight:")[1].split()[0])
        bg = f"data:image/jpeg;base64,{base64.b64encode(p.read_bytes()).decode()}"
    html = build_html(primitives.select(primitives.discover(), cfg.primitives))
    boot = f"""<style>html,body{{background:#555 url('{bg}') 0 0/100% 100% no-repeat !important}}</style>
<script>addEventListener("load",()=>{{U.begin({{imgW:{w},imgH:{h}}});U.end();
const ops={json.dumps(ops)};let i=0;(function next(){{if(i<ops.length){{U.apply(ops[i++]);setTimeout(next,40)}}}})();}});</script>"""
    Path(args.out).write_text(html.replace("</body>", boot + "</body>"))
    print(args.out)
