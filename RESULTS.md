# CardKS results

[← Back to CardKS](README.md)

This page transcribes the quantitative tables from the current CardKS manuscript into readable Markdown. The values are **reported paper results**, not live CI benchmarks, and the full public reproduction bundle—code for all three games, checkpoints, seed manifests, and raw evaluation outputs—is not yet available.

## Evaluation protocols

| Game | Specialized evaluation | Variance control | Reported metrics |
| --- | --- | --- | --- |
| GuanDan | 5,000 paired configurations; 10,000 promotion matches from level 2 to A | Partnership swapping | Game WR, Round WR, mean round value in `{±1, ±2, ±3}` |
| DouDizhu | 5,000 paired deals; 10,000 games; bidding disabled | Landlord/Peasant role swapping | WP, ADP, Landlord WP, Peasant WP |
| Gin Rummy | 5,000 paired seeds; 10,000 hands | Seat swapping | Method WR, positive reward rate, mean RLCard payoff |

Language-model baselines use smaller budgets: 20 GuanDan matches, 500 paired DouDizhu deals, and 50 paired Gin Rummy seeds.

## Head-to-head evaluation

### Complete GuanDan promotion matches

| Opponent | Game WR | Round WR | Mean round value |
| --- | ---: | ---: | ---: |
| DanZero | 71.50% | 52.60% | 0.1190 |
| DanZero+ | 96.50% | 69.95% | 1.2991 |
| RuleBot-ai2 | 65.80% | 56.05% | 1.2420 |
| Prompt-only | 100.00% | 100.00% | 3.0000 |
| Qwen2.5-7B-Instruct-single | 100.00% | 76.88% | 1.6063 |

Two DanKS agents partner against two copies of each opponent policy.

### DouDizhu baselines

| Opponent | WP | ADP | Landlord WP | Peasant WP |
| --- | ---: | ---: | ---: | ---: |
| RandomAgent | 98.96% | 3.1159 | 98.45% | 99.47% |
| CQN | 82.85% | 2.3298 | 80.04% | 85.65% |
| DouZero | 54.00% | 0.1953 | 50.50% | 57.50% |
| PerfectDou | 53.00% | 0.1125 | 49.80% | 56.20% |
| RLCard RuleAgentV1 | 86.90% | 2.1922 | 85.52% | 88.27% |
| Prompt-only | 97.60% | 2.9900 | 96.40% | 98.80% |
| Qwen2.5-7B-Instruct-single | 87.40% | 2.0760 | 87.60% | 87.20% |

ADP includes bomb and rocket multipliers.

### Gin Rummy single-hand protocol

| Opponent | Method WR | Positive rate | Mean payoff |
| --- | ---: | ---: | ---: |
| RandomAgent | 99.35% | 99.37% | 0.231641 |
| GinRummyNoviceRuleAgent | 74.49% | 74.42% | 0.101117 |
| IRumAI | 58.37% | 58.22% | 0.018623 |
| EAAI DNN Heuristic | 54.59% | 66.91% | 0.066000 |
| EAAI Dual Inception | 57.87% | 68.57% | 0.076190 |
| Prompt-only | 98.00% | 98.00% | 0.247200 |
| Qwen2.5-7B-Instruct-single | 93.00% | 93.00% | 0.184900 |

Win rate, reward sign, and payoff are reported together because Knock and Undercut can make them disagree.

## Ablation study

All variants play fixed rule-based opponents: RuleBot-ai2 for GuanDan, RLCard RuleAgentV1 for DouDizhu, and GinRummyNoviceRuleAgent for Gin Rummy.

| Method | GuanDan | DouDizhu | Gin Rummy |
| --- | ---: | ---: | ---: |
| **CardKS** | **65.80%** | **86.90%** | **74.49%** |
| TopK-Top1 | 16.40% | 54.30% | 55.40% |
| TopK-Random | 3.53% | 11.83% | 0.97% |
| Legal-Random | 1.93% | 5.60% | 0.80% |
| w/o Policy Structure | 2.60% | 11.50% | 17.90% |
| w/o Residual Structure | 0.20% | 7.80% | 20.24% |

TopK-Random consistently exceeds Legal-Random, showing that structured retrieval concentrates stronger actions. Full CardKS remains substantially above TopK-Top1, showing that the learned policy is still essential for context-dependent selection.

## Candidate support quality

Recall@K is the fraction of held-out states whose Top-K set contains an expert action or a rule-equivalent action. These human decisions are used for evaluation and are excluded from PPO training.

| Ranker | Held-out decisions | R@1 | R@3 | R@5 | R@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| DanKS | 32,174 | 57.38% | 86.40% | 93.09% | 97.30% |
| DouKS | 10,528 | 49.00% | 85.00% | 95.00% | 99.00% |
| RummyKS | 21,783 | 41.00% | 79.00% | 94.00% | 100.00% |

The jump from R@1 to R@5 shows that the ranker identifies a compact expert-relevant neighborhood even when the reference action is not ranked first.

## Language-model candidate interface

The prompt-only language model, state representation, prompt, and decoding settings are fixed; only the visible action set changes. “Primary metric” is the game-specific payoff measure. “Valid / fallback” gives the percentages of valid decisions and fallback decisions.

### GuanDan

| Candidates | Win rate | Primary metric | Valid / fallback |
| --- | ---: | ---: | ---: |
| **CardKS-Top10** | **12.20%** | **-2.2130** | **99.73 / 0.27** |
| FullLegal | 5.60% | -2.4240 | 99.30 / 0.70 |
| Random-Top10 | 2.60% | -2.6680 | 99.36 / 0.64 |

### DouDizhu

| Candidates | Win rate | Primary metric | Valid / fallback |
| --- | ---: | ---: | ---: |
| **CardKS-Top10** | **16.20%** | **-2.0040** | **86.47 / 13.53** |
| FullLegal | 8.90% | -2.3880 | 82.22 / 17.78 |
| Random-Top10 | 6.40% | -2.4860 | 85.65 / 14.35 |

### Gin Rummy

| Candidates | Win rate | Primary metric | Valid / fallback |
| --- | ---: | ---: | ---: |
| **CardKS-Top10** | **7.35%** | **-0.2330** | **98.96 / 1.04** |
| FullLegal | 1.20% | -0.6085 | 97.32 / 2.68 |
| Random-Top10 | 0.50% | -0.6230 | 98.54 / 1.46 |

Relative to FullLegal, CardKS-Top10 raises win rate by 6.60, 7.30, and 6.15 percentage points in GuanDan, DouDizhu, and Gin Rummy, respectively.

## Computational efficiency

### Simulation efficiency

| Game | Environment | Legal (ms) ↓ | 1-core DPS ↑ | 32-env DPS ↑ | Speedup ↑ |
| --- | --- | ---: | ---: | ---: | ---: |
| GuanDan | DanZero Platform | 0.0992 | 4,210.80 | 43,273.20 | 1.00x |
| GuanDan | **KSPlay** | **0.0702** | **4,424.47** | **56,638.51** | **1.31x** |
| DouDizhu | DouZero Environment | 0.0171 | 8,687.97 | 127,042.90 | 1.00x |
| DouDizhu | **KSPlay** | **0.0066** | **15,644.31** | **267,242.16** | **2.10x** |
| Gin Rummy | RLCard Runtime | 0.0103 | 40,261.28 | 536,786.13 | 1.00x |
| Gin Rummy | **KSPlay** | **0.0002** | **45,300.87** | **704,994.15** | **1.31x** |

DPS denotes environment decisions per second; speedup is measured against each reference environment at 32 parallel environments.

### Online decision efficiency

| Game | Method | Preprocessing (ms) ↓ | Network (ms) ↓ | Complete decision (ms) ↓ |
| --- | --- | ---: | ---: | ---: |
| GuanDan | DanZero | **0.6964** | 0.9008 | **1.5984** |
| GuanDan | DanZero+ | 0.7716 | 1.2231 | 1.9971 |
| GuanDan | **DanKS** | 1.8161 | **0.3722** | 2.2592 |
| DouDizhu | DouZero | **0.2926** | 0.9845 | **1.2790** |
| DouDizhu | PerfectDou | 1.9252 | 1.1768 | 3.3080 |
| DouDizhu | **DouKS** | 1.2694 | **0.9572** | 2.2288 |
| Gin Rummy | EAAI DNN Heuristic | 57.6606 | 4.8977 | 62.5583 |
| Gin Rummy | EAAI Dual Inception | 119.6296 | 12.8195 | 132.4491 |
| Gin Rummy | **RummyKS** | **0.2667** | **0.1941** | **0.4619** |

## Implementation snapshot

| Setting | DanKS | DouKS | RummyKS |
| --- | ---: | ---: | ---: |
| State / candidate feature dimensions | 122 / 117 | 165 / 89 | 283 / 90 |
| AdamW learning rate | 1e-5 | 1e-4 | 1e-4 |
| Mini-batch size | 8,192 | 8,192 | 1,024 |
| PPO epochs | 1 | 4 | 4 |
| Effective player decisions | 5.13e8 | 6.48e8 | 1.46e9 |

All three use structured Top-10 candidates, deterministic inference, `γ = 0.99`, GAE `λ = 0.95`, and PPO clip range `0.08`. DouKS maintains separate Landlord and Peasant policies; RummyKS shares parameters across seats. The manuscript training hardware is 192 Intel Xeon Platinum 8468 CPU cores and eight NVIDIA H100 GPUs.

## Dataset snapshot

KSCB is constructed from de-identified, replay-validated human-play records:

| Split source | Complete units | Decision points |
| --- | ---: | ---: |
| GuanDan promotion matches | 899 matches | 840,194 |
| GuanDan replay-validated rounds | 10,738 rounds | 884,272 |
| DouDizhu games | 947 games | 28,083 |

The current manuscript states that processed KSCB records are planned for release under CC BY-NC 4.0. Original logs, identity mappings, and account, device, network, chat, or other identifying fields remain private. Gin Rummy uses the public Arkadium dataset after the same replay-validation procedure.

## Reproduction boundary

- Results use fixed rules, paired deals or seeds, and role or partnership swapping.
- The tables above are transcribed from the manuscript source; that source is not part of this repository.
- No model checkpoint, benchmark payload, raw match log, or seed manifest is included here.
- Final values may change during review or camera-ready preparation.
