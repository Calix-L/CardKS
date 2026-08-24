# KS Card Benchmark (KSCB)

KSCB is the human game-trajectory benchmark used by CardKS. It contains GuanDan promotion matches and complete three-player DouDizhu games, with ordered gameplay events and terminal outcomes.

## Data

- `data/guandan_matches.jsonl.gz`: 1,305 complete promotion matches containing 14,823 rounds.
- `data/doudizhu_games.jsonl.gz`: 947 complete three-player games.

Both files use JSON Lines compressed with gzip.

## GuanDan records

Each line of `guandan_matches.jsonl.gz` is one promotion match with:

- `sample_id`, `game`, `schema_version`, and `round_count`;
- `rounds`, the ordered list of rounds in the match;
- per-round players, game rules, ordered events, cards, and terminal result;
- `result_type`, `win_type`, and each player's `win_index` in the result.

GuanDan decision events use event type 3 for play and event type 4 for PASS.

## DouDizhu records

Each line of `doudizhu_games.jsonl.gz` is one complete game with:

- `sample_id`, `game`, and `schema_version`;
- players, game rules, ordered events, cards, and terminal result;
- terminal hands, bomb count, spring indicator, and each player's `is_winner` value.

DouDizhu decision events use event type 9 for play and event type 10 for PASS.
