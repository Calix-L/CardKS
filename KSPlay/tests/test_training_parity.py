from __future__ import annotations

import json
import random

import pytest

import ksplay
from ksplay.games.guandan import Environment as GuanDanEnvironment
from ksplay.games.guandan import python_rules


PLAYERS = {
    "guandan": ["a", "b", "c", "d"],
    "doudizhu": ["a", "b", "c"],
    "gin-rummy": ["a", "b"],
}


def _run(game: str, fast: bool) -> tuple[list[tuple[int, str]], object]:
    session = ksplay.make(game, seed=37, training_fast_path=fast)
    messages = session.reset(PLAYERS[game])
    transcript: list[tuple[int, str]] = []

    for _ in range(20_000):
        transcript.extend(
            (message.seat, json.dumps(message.body, sort_keys=True))
            for message in messages
        )
        if session.table.results is not None:
            return transcript, session.table.results
        messages = session.step(session.current_seat, len(session.legal_actions) - 1)
    raise AssertionError(f"{game} did not finish")


@pytest.mark.parametrize("game", list(PLAYERS))
def test_training_fast_path_preserves_complete_game_semantics(game: str) -> None:
    strict_transcript, strict_result = _run(game, False)
    fast_transcript, fast_result = _run(game, True)

    assert fast_transcript == strict_transcript
    assert fast_result == strict_result


def _global_seed_opening(seed: int) -> list[tuple[int, str]]:
    random.seed(seed)
    table = GuanDanEnvironment()
    for seat in range(4):
        table.add_player(str(seat), seat)
    return [
        (message.seat, json.dumps(message.body, sort_keys=True))
        for message in table.start()
    ]


def test_guandan_without_explicit_seed_preserves_training_global_rng_contract() -> None:
    assert _global_seed_opening(101) == _global_seed_opening(101)


def test_guandan_accepts_the_training_rule_profile_environment(monkeypatch) -> None:
    monkeypatch.delenv("KSPLAY_GUANDAN_RULE_PROFILE", raising=False)
    monkeypatch.setenv("DAN_PLATFORM_RULE_PROFILE", "arena_client_pdf_v1")

    assert python_rules._rule_profile() == "arena_client_pdf_v1"
