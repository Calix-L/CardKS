# KS Card Benchmark (KSCB)

KSCB is the replay-validated human decision benchmark used by CardKS.

## Public deidentified sample

[`data/`](./data) contains deterministic samples from the benchmark reported in the paper appendix:

- `kscb_guandan_promotion_matches_5pct.jsonl`: 44 promotion matches containing 508 rounds.
- `kscb_guandan_replay_valid_rounds_5pct.jsonl`: 536 replay-validated rounds.
- `kscb_doudizhu_games_5pct.jsonl`: 47 complete three-player games.
- `kscb_sample_manifest.json`: sample counts, hashes, selection rules, and deidentification notes.

These are approximately 5% public samples, not the full KSCB collections (899 GuanDan promotion matches, 10,738 replay-valid GuanDan rounds, and 947 complete DouDizhu games). Ordered gameplay events and terminal outcomes are preserved. Player identifiers use trajectory-local aliases, while identifying, account, company/platform, room/table/replay, absolute-time, device/network/location, chat, and media fields are removed.

Raw logs and identity mappings are not released.
