from __future__ import annotations

import pytest

import ksplay


@pytest.mark.parametrize(
    ("game", "players"),
    [
        ("guandan", ["north", "east", "south", "west"]),
        ("doudizhu", ["landlord", "farmer-a", "farmer-b"]),
        ("gin-rummy", ["alice", "bob"]),
    ],
)
def test_each_game_starts_through_one_api(game: str, players: list[str]) -> None:
    session = ksplay.make(game, seed=7, training_fast_path=True)
    opening = session.reset(players)

    assert session.game == game
    assert session.player_count == len(players)
    assert isinstance(opening, list)
    assert session.current_seat in range(len(players))
    assert session.legal_actions


def test_unknown_game_has_a_useful_error() -> None:
    with pytest.raises(ValueError, match="guandan.*doudizhu.*gin-rummy"):
        ksplay.make("poker")


def test_guandan_automatic_phase_boundaries_do_not_require_fake_actions() -> None:
    session = ksplay.make("guandan", seed=7, training_fast_path=True)
    session.reset(["a", "b", "c", "d"])

    for _ in range(500):
        if session.table.results is not None:
            break
        session.step(session.current_seat, 0)


def test_doudizhu_exposes_each_simultaneous_double_seat() -> None:
    session = ksplay.make("doudizhu", seed=7, training_fast_path=True)
    session.reset(["a", "b", "c"])
    session.step(session.current_seat, len(session.legal_actions) - 1)

    first_defender = session.current_seat
    session.step(first_defender, 0)
    assert session.current_seat != first_defender
