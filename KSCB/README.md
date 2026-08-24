# KS Card Benchmark (KSCB)

KSCB provides source-derived, deidentified human game trajectories for GuanDan and DouDizhu.

## Data

- `data/guandan_matches.jsonl.gz`: 1,305 complete promotion matches containing 14,823 rounds.
- `data/guandan_rounds.jsonl.gz`: 14,878 completed, deduplicated rounds.
- `data/doudizhu_games.jsonl.gz`: 947 complete three-player games.
- `data/manifest.json`: source criteria, counts, and file hashes.
- `data/audit.json`: full-file privacy, structure, result, winner, count, and hash checks.

The two GuanDan files are overlapping views and must not be added together. These are the complete source-derived units that satisfy the stated criteria, not a reconstruction of a separately normalized paper target. The GuanDan round view is completion-qualified and is not labeled rule-engine replay-valid.

Ordered events and terminal outcomes are preserved. Player and record identifiers use release-local aliases; profile, account, company/platform, replay/room/table, absolute-time, device/network/location, chat, media, balance, and related fields are removed. Raw logs and identity mappings are not released.
