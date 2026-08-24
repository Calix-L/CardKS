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


@pytest.mark.parametrize("game", ["guandan", "doudizhu", "gin-rummy"])
def test_first_reset_reuses_the_prepared_engine(game: str) -> None:
    session = ksplay.make(game, seed=7, training_fast_path=True)
    prepared = session.table

    session.reset({
        "guandan": ["a", "b", "c", "d"],
        "doudizhu": ["a", "b", "c"],
        "gin-rummy": ["a", "b"],
    }[game])

    assert session.table is prepared


def test_training_mode_reaches_each_engine_without_trace_or_copy_features() -> None:
    guandan = ksplay.make("guandan", training_fast_path=True)
    doudizhu = ksplay.make("doudizhu", training_fast_path=True)
    rummy = ksplay.make("gin-rummy", training_fast_path=True)

    assert guandan.table.allow_step_back is False
    assert doudizhu.table.allow_step_back is False
    assert doudizhu.table.training_fast_path is True
    assert rummy.table.allow_step_back is False
    assert rummy.table.record_trace is False
    assert rummy.table.training_fast_path is True
