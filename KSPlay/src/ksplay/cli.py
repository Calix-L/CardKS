"""Command-line entry points for verification and serving."""

from __future__ import annotations

import argparse
import asyncio
import json
from time import perf_counter

from . import make
from .server.websocket import run_server


PLAYERS = {
    "guandan": ["north", "east", "south", "west"],
    "doudizhu": ["landlord", "farmer-a", "farmer-b"],
    "gin-rummy": ["north", "south"],
}


def _run_game(game: str, *, max_steps: int = 20_000) -> tuple[int, float]:
    session = make(game, seed=7, training_fast_path=True)
    session.reset(PLAYERS[game])
    started = perf_counter()
    steps = 0
    while steps < max_steps and getattr(session.table, "results", None) is None:
        session.step(session.current_seat, len(session.legal_actions) - 1)
        steps += 1
    session.close()
    return steps, perf_counter() - started


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ksplay")
    commands = parser.add_subparsers(dest="command", required=True)
    smoke = commands.add_parser("smoke", help="play deterministic smoke games")
    smoke.add_argument("--game", choices=["all", *PLAYERS], default="all")
    benchmark = commands.add_parser("benchmark", help="measure direct engine steps")
    benchmark.add_argument("--game", choices=list(PLAYERS), default="guandan")
    serve_parser = commands.add_parser("serve", help="start the shared WebSocket service")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    if args.command == "serve":
        asyncio.run(run_server(args.host, args.port))
        return 0
    games = list(PLAYERS) if args.command == "smoke" and args.game == "all" else [args.game]
    report = {}
    for game in games:
        steps, elapsed = _run_game(game)
        report[game] = {
            "steps": steps,
            "seconds": round(elapsed, 4),
            "steps_per_second": round(steps / max(elapsed, 1e-9), 1),
        }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
