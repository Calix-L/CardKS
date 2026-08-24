# KS Card Benchmark (KSCB)

KSCB provides source-derived, deidentified human game trajectories for GuanDan and DouDizhu.

## Data

- `data/guandan_matches.jsonl.gz`: 1,305 complete promotion matches containing 14,823 rounds.
- `data/doudizhu_games.jsonl.gz`: 947 complete three-player games.

The GuanDan file contains all deduplicated promotion matches for which every observed round is complete. All released units satisfy the stated selection criteria.

Ordered events and terminal outcomes are preserved. Player and record identifiers use release-local aliases; profile, account, company/platform, replay/room/table, absolute-time, device/network/location, chat, media, balance, and related fields are removed. Raw logs and identity mappings are not released.
