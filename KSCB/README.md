# KS Card Benchmark (KSCB)

KSCB is the human game-trajectory dataset introduced with CardKS. It contains GuanDan promotion matches and complete three-player DouDizhu games. Each record preserves gameplay events in their original order together with the terminal result.

## Data Files

| File | Game | Record Unit | Format |
| --- | --- | --- | --- |
| `data/guandan_matches.jsonl.gz` | GuanDan | One promotion match containing an ordered sequence of rounds | gzip-compressed JSON Lines |
| `data/doudizhu_games.jsonl.gz` | DouDizhu | One complete three-player game | gzip-compressed JSON Lines |

After decompression, every line is an independent JSON object.

## Dataset Scale

KSCB is reported at three trajectory levels.

| Game | Collection | Size | Decision Points | Decisions per Unit |
| --- | --- | ---: | ---: | ---: |
| GuanDan | Complete promotion matches | 899 matches / 10,218 internal rounds | 840,194 | 934.59 per match |
| GuanDan | Replay-validated rounds | 10,738 rounds | 884,272 | 82.35 per round |
| DouDizhu | Complete games | 947 games | 28,083 | 29.65 per game |

The 899 complete GuanDan promotion matches contain 10,218 internal rounds. The promotion-match collection and the 10,738 replay-validated round collection represent different trajectory levels and are not added together.

## GuanDan Data Format

A GuanDan record represents one promotion match. The match contains an ordered `rounds` array. Each round includes four players, the game rules, an ordered event sequence, and the terminal result.

```json
{
  "game": "GuanDan",
  "sample_id": "GD_MATCH_0002",
  "round_count": 8,
  "rounds": [
    {
      "game": "GuanDan",
      "sample_id": "GD_MATCH_0002_ROUND_001",
      "match_id": "GD_MATCH_0002",
      "players": [
        {
          "chair_id": 1,
          "uid": "P1"
        },
        {
          "chair_id": 2,
          "uid": "P2"
        },
        {
          "chair_id": 3,
          "uid": "P3"
        },
        {
          "chair_id": 4,
          "uid": "P4"
        }
      ],
      "game_rule": "{\"extra\":{\"double\":0,\"ending\":1,\"level_up\":1,\"mode\":1,\"tribute\":1}}",
      "events": [
        {
          "event_id": 3,
          "uid": "P4",
          "tiles": [20],
          "pattern": 1,
          "fan": 1
        },
        ...
        {
          "event_id": 4,
          "uid": "P4"
        }
      ],
      "result": {
        "result_type": 1,
        "win_type": 1,
        "levelup": 3,
        "score": 3,
        "players": [
          {
            "uid": "P1",
            "is_banker": false,
            "win_index": 4,
            "hand": [23, 27, 39, ...]
          },
          {
            "uid": "P2",
            "is_banker": true,
            "win_index": 2,
            "hand": null
          },
          {
            "uid": "P3",
            "is_banker": false,
            "win_index": 3,
            "hand": [17, 33, 53, ...]
          },
          {
            "uid": "P4",
            "is_banker": true,
            "win_index": 1,
            "hand": null
          }
        ]
      }
    },
    ...
  ]
}
```

The `events` array follows gameplay order. For decision events, `event_id` 3 represents a play and `event_id` 4 represents PASS.

### GuanDan Terminal Results

- `result_type` is the terminal-result status code. Complete rounds use value `1`.
- `win_index` records finishing order: `1` for first, `2` for second, `3` for third, and `4` for fourth.
- `win_type` records the partnership finishing pattern:
  - `1`: the first- and second-place players are partners;
  - `2`: the first- and third-place players are partners;
  - `3`: the first- and fourth-place players are partners.
- `score` records the promotion score associated with the finishing pattern: `3`, `2`, or `1`, respectively.
- `levelup` records the level increment applied to the current promotion-match state.
- `is_banker` identifies the banker-side partnership for the round. Players with the same value belong to the same partnership.
- `hand` contains the cards remaining at termination. `null` indicates that the player has emptied their hand.

## DouDizhu Data Format

A DouDizhu record represents one complete three-player game. It contains the three players, the landlord identifier, game rules, the ordered event sequence, and the terminal result.

```json
{
  "game": "DouDizhu",
  "sample_id": "DDZ_GAME_000001",
  "players": [
    {
      "chair_id": 1,
      "uid": "P1"
    },
    {
      "chair_id": 2,
      "uid": "P2"
    },
    {
      "chair_id": 3,
      "uid": "P3"
    }
  ],
  "banker": "P2",
  "dice": [],
  "game_rule": "{\"bu_xi_pai\":false,\"is_double\":false,\"ming_pai\":false,\"quickplay\":false}",
  "max_mj_count": 0,
  "remain_mjs": [],
  "events": [
    {
      "event_id": 9,
      "uid": "P2",
      "bei_shu": 1,
      "data": {
        "seatid": 2,
        "cardlist": [59, 26, 25, 56, ...],
        "handcardcount": 12
      }
    },
    {
      "event_id": 10,
      "uid": "P3",
      "data": {
        "seatid": 3
      }
    },
    ...
  ],
  "result": {
    "result_type": 1,
    "bomb_count": 0,
    "is_spring": false,
    "players": [
      {
        "uid": "P2",
        "chair_id": 2,
        "bomb_count": 0,
        "is_winner": true,
        "hand": []
      },
      {
        "uid": "P3",
        "chair_id": 3,
        "bomb_count": 0,
        "is_winner": false,
        "hand": [24, 30, 40, ...]
      },
      {
        "uid": "P1",
        "chair_id": 1,
        "bomb_count": 0,
        "is_winner": false,
        "hand": [28, 31, 35, ...]
      }
    ]
  }
}
```

The `banker` value identifies the landlord. The `events` array follows gameplay order. For decision events, `event_id` 9 represents a play and `event_id` 10 represents PASS.

### DouDizhu Terminal Results

- `result_type` is the terminal-result status code. Complete games use value `1`.
- The result-level `bomb_count` is the total number of bomb actions counted in the game.
- Each result player also has a `bomb_count` recording the number attributed to that player.
- `is_spring` indicates whether the game ended with a spring result.
- `is_winner` marks the player recorded as the terminal winner.
- `hand` contains the cards remaining in that player's hand at termination. The terminal winner has an empty hand.

## Reading the Files

```python
import gzip
import json


def read_jsonl_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as file:
        for line in file:
            yield json.loads(line)


for match in read_jsonl_gz("data/guandan_matches.jsonl.gz"):
    print(match["sample_id"], match["round_count"])
    break

for game in read_jsonl_gz("data/doudizhu_games.jsonl.gz"):
    print(game["sample_id"], game["result"])
    break
```

The `game_rule` value is a serialized JSON string and can be decoded with `json.loads(record["game_rule"])`. Card values in fields such as `tiles`, `cardlist`, and `hand` are represented by integer card codes.
