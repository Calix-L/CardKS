<p align="right">
  <a href="README.md">English</a> · <strong>简体中文</strong>
</p>

# KS Card Benchmark（KSCB）

KSCB 是随 CardKS 论文提出的人类牌局轨迹数据集，包含掼蛋升级赛和完整的三人斗地主对局。每条记录保留按照原始游戏顺序排列的事件以及对应的终局结果。

## 数据文件

| 文件 | 游戏 | 记录单位 | 格式 |
| --- | --- | --- | --- |
| `data/guandan_matches.jsonl.gz` | 掼蛋 | 一场由多个有序单局组成的升级赛 | gzip 压缩的 JSON Lines |
| `data/doudizhu_games.jsonl.gz` | 斗地主 | 一局完整的三人斗地主对局 | gzip 压缩的 JSON Lines |

文件解压后，每一行都是一个独立的 JSON 对象。

## 数据集规模

KSCB 按照三个轨迹层级进行统计。

| 游戏 | 数据集合 | 规模 | 决策点 | 单位平均决策数 |
| --- | --- | ---: | ---: | ---: |
| 掼蛋 | 完整升级赛 | 899 场升级赛 / 10,218 个内部小局 | 840,194 | 每场 934.59 个 |
| 掼蛋 | 规则重放验证小局 | 10,738 个小局 | 884,272 | 每个小局 82.35 个 |
| 斗地主 | 完整对局 | 947 局 | 28,083 | 每局 29.65 个 |

899 场完整掼蛋升级赛包含 10,218 个内部小局。升级赛集合与包含 10,738 个小局的规则重放验证集合属于不同的轨迹统计层级，两者不直接相加。

## 掼蛋数据格式

一条掼蛋记录表示一场升级赛。升级赛通过 `rounds` 数组按顺序保存其中的单局。每个单局包含四名玩家、游戏规则、有序事件序列和终局结果。

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

`events` 数组按照游戏发生顺序排列。在决策事件中，`event_id` 为 `3` 表示出牌，为 `4` 表示 PASS。

### 掼蛋终局结果

- `result_type` 是终局结果状态码。完整单局使用取值 `1`。
- `win_index` 表示玩家的完赛顺序：`1` 为头游，`2` 为二游，`3` 为三游，`4` 为末游。
- `win_type` 表示同队玩家的完赛组合：
  - `1`：头游和二游为同队玩家；
  - `2`：头游和三游为同队玩家；
  - `3`：头游和末游为同队玩家。
- `score` 表示该完赛组合对应的升级分值，以上三种情况依次为 `3`、`2` 和 `1`。
- `levelup` 表示根据当前升级赛状态实际应用的升级级数。
- `is_banker` 表示玩家是否属于该单局的庄家方。取值相同的玩家属于同一队。
- `hand` 保存终局时玩家剩余的手牌；`null` 表示该玩家已经出完手牌。

## 斗地主数据格式

一条斗地主记录表示一局完整的三人游戏，包含三名玩家、地主标识、游戏规则、有序事件序列和终局结果。

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

`banker` 表示地主玩家。`events` 数组按照游戏发生顺序排列。在决策事件中，`event_id` 为 `9` 表示出牌，为 `10` 表示 PASS。

### 斗地主终局结果

- `result_type` 是终局结果状态码。完整对局使用取值 `1`。
- 结果顶层的 `bomb_count` 表示该局中计入终局结果的炸弹动作总数。
- 每名结果玩家也包含 `bomb_count`，表示计入该玩家名下的炸弹数量。
- `is_spring` 表示该局是否以春天结果结束。
- `is_winner` 标记终局记录中的获胜玩家。
- `hand` 保存终局时该玩家剩余的手牌；终局获胜玩家的手牌为空数组。

## 读取数据

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

`game_rule` 的值是一个经过序列化的 JSON 字符串，可以使用 `json.loads(record["game_rule"])` 解码。`tiles`、`cardlist` 和 `hand` 等字段中的牌使用整数牌值编码。
