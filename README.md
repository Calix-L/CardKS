<p align="right">
  <strong>English</strong> · <a href="README.zh-CN.md">简体中文</a>
</p>

<h1 align="center">CardKS</h1>

<p align="center">
  <strong>Residual Key-Structure Modeling for Long-Horizon Decisions</strong>
</p>

<p align="center">
  One structural decision framework · Three imperfect-information card games · State-of-the-art performance
</p>

<p align="center">
  <a href="#one-paper-three-contributions">Contributions</a> ·
  <a href="#main-results">Results</a> ·
  <a href="#how-cardks-works">Method</a> ·
  <a href="#research-suite">Research suite</a> ·
  <a href="RESULTS.md">Full tables</a> ·
  <a href="#citation">Citation</a>
</p>

<p align="center">
  <a href="LICENSE"><img alt="Apache-2.0 license" src="https://img.shields.io/badge/license-Apache--2.0-D22128"></a>
  <img alt="State of the art across three games" src="https://img.shields.io/badge/SOTA-3_card_games-5865F2">
  <img alt="Top-5 expert action recall" src="https://img.shields.io/badge/Top--5_recall-93.09%25%E2%80%9395.00%25-1F9D72">
  <img alt="KSPlay throughput speedup" src="https://img.shields.io/badge/KSPlay-up_to_2.10%C3%97-F59E0B">
</p>

<p align="center">
  <a href="assets/cardks-framework.webp"><img src="assets/cardks-framework.webp" alt="CardKS framework: information state, structured candidate ranker, Actor-Critic, and PPO self-play" width="960"></a><br>
  <sub><strong>Framework.</strong> Information state, structure-aware retrieval, candidate-conditioned Actor-Critic, and PPO self-play.</sub>
</p>

CardKS is a unified framework for long-horizon decision-making in imperfect-information card games with large combinatorial action spaces. Its central observation is simple: **an action changes both the current position and the structure of every future decision**.

CardKS evaluates legal actions through the key structures they preserve in the residual hand, retrieves a compact and diverse Top-K candidate set, and learns context-dependent selection with a candidate-conditioned Actor-Critic trained by PPO self-play. The same design powers **DanKS** for GuanDan, **DouKS** for DouDizhu, and **RummyKS** for Gin Rummy.

> **Retrieve actions that preserve future options. Learn when each option creates long-term value.**

## One paper, three contributions

| **CardKS · Decision framework** | **KSCB · Human benchmark** | **KSPlay · Scalable platform** |
| --- | --- | --- |
| Structure-aware candidate retrieval and candidate-conditioned Actor-Critic learning | The first expert-level benchmark spanning both GuanDan and DouDizhu | Rules-as-code, parallel simulation, distributed evaluation, self-play, and online inference |
| SOTA results across all three games with 93.09%–95.00% Top-5 expert-action recall | Replay-validated trajectories for learning, evaluation, and candidate analysis | Up to 2.10× higher 32-environment throughput with low-millisecond decisions |

## Main results

CardKS reaches state-of-the-art performance across cooperative, asymmetric-role, and two-player card games.

| Game | CardKS agent | Representative opponent | Head-to-head result |
| --- | --- | --- | ---: |
| GuanDan | **DanKS** | DanZero | **71.50%** game win rate |
| DouDizhu | **DouKS** | DouZero | **54.00%** win rate |
| Gin Rummy | **RummyKS** | IRumAI | **58.37%** method win rate |

<p align="center">
  <a href="assets/main-results.webp"><img src="assets/main-results.webp" alt="Main CardKS results for GuanDan, DouDizhu, and Gin Rummy" width="500"></a><br>
  <sub><strong>Table 1.</strong> Head-to-head results under game-specific paired-deal, seed, and role-swapping protocols.</sub>
</p>

The results show one method transferring across three fundamentally different interaction structures:

- **GuanDan:** four-player partnership play with cooperation, hidden hands, and promotion-match outcomes.
- **DouDizhu:** asymmetric Landlord and Peasant roles with role-dependent objectives.
- **Gin Rummy:** two-player sequential play with meld preservation, knock timing, and payoff-sensitive endings.

### What drives the gain?

<p align="center">
  <a href="assets/ablation-results.webp"><img src="assets/ablation-results.webp" alt="CardKS ablation results across all three games" width="720"></a><br>
  <sub><strong>Table 2.</strong> Win rates against fixed rule-based opponents.</sub>
</p>

Full CardKS exceeds the deterministic **TopK-Top1** selector by **49.40**, **32.60**, and **19.09** percentage points in GuanDan, DouDizhu, and Gin Rummy. Structured retrieval concentrates strong actions; the learned policy supplies the state-dependent judgment needed to choose among them.

The candidate rankers retain **93.09%–95.00%** of expert-equivalent actions at Top-5 and **97.30%–100.00%** at Top-10. This creates a compact decision interface that works for PPO policies and also improves language-model action selection.

All protocols, per-opponent results, candidate Recall@K, language-model experiments, efficiency measurements, and implementation settings are available in [**RESULTS.md**](RESULTS.md).

## How CardKS works

| Stage | Core operation | Why it matters |
| --- | --- | --- |
| **1 · Observe** | Encode the visible hand, public history, seat context, and legal actions. | Builds the acting player's information state. |
| **2 · Retrieve** | Apply each action and search legal decompositions of the residual hand. | Exposes pairs, sequences, suits, gaps, and future action structure. |
| **3 · Select** | Jointly encode state, candidate action, and residual-structure summary. | Lets the Actor rank a compact Top-K set while the Critic estimates long-term value. |
| **4 · Learn** | Optimize the candidate policy with PPO, GAE, and online self-play. | Assigns credit to structural choices whose payoff appears several decisions later. |

The structured ranker and learned policy solve complementary parts of the problem. Retrieval preserves a high-quality support set before policy optimization; the Actor-Critic then adapts candidate priorities to the current information state.

## Emergent long-horizon strategies

CardKS learns decisions that trade immediate card reduction for future control. In one trajectory it preserves a high pair and regains initiative later; in another it passes to protect the only winning pair-straight continuation.

<p align="center">
  <a href="assets/emergent-strategies.webp"><img src="assets/emergent-strategies.webp" alt="Two CardKS case studies showing initiative recovery and pair-straight preservation" width="820"></a><br>
  <sub><strong>Case studies.</strong> Preserving initiative and protecting the only winning pair-straight continuation.</sub>
</p>

These behaviors emerge from residual-structure modeling and self-play, connecting the model's representation directly to recognizable long-horizon strategy.

## Research suite

CardKS is the paper-level home for a six-part research suite:

| Project | Role in the paper | Repository |
| --- | --- | --- |
| **DanKS** | GuanDan agent, three generations of retrieval and PPO implementation | [Calix-L/DanKS ↗](https://github.com/Calix-L/DanKS) |
| **DouKS** | DouDizhu agent with Landlord- and Peasant-aware policies | [Calix-L/DouKS ↗](https://github.com/Calix-L/DouKS) |
| **RummyKS** | Gin Rummy agent with residual meld-structure modeling | [Calix-L/RummyKS ↗](https://github.com/Calix-L/RummyKS) |
| **KSPlay** | Shared rules, simulation, self-play, and evaluation platform | [Open KSPlay](./KSPlay) |
| **KS Card Benchmark** | Replay-validated human trajectories for GuanDan and DouDizhu | [Open KSCB](./KSCB) |
| **CardKS results** | Protocols, full tables, ablations, recall, and efficiency | [Open RESULTS.md](RESULTS.md) |

The three game agents are linked as Git submodules, so each directory opens its independent repository directly from the CardKS project tree. KSPlay and KSCB live alongside the paper overview as shared cross-game resources.

### KSPlay: one platform across games

KSPlay unifies rule execution, parallel simulation, distributed policy evaluation, high-throughput self-play, and online inference. At 32 parallel environments, it reaches **1.31×**, **2.10×**, and **1.31×** the reference throughput in GuanDan, DouDizhu, and Gin Rummy. CardKS end-to-end decisions remain below **2.26 ms** across all three games.

### KSCB: human decisions at game scale

The public KS Card Benchmark currently contains **1,305 complete GuanDan promotion matches spanning 14,823 rounds** and **947 complete DouDizhu games**. Every trajectory follows a compact JSONL schema with ordered events and terminal outcomes, supporting imitation learning, offline reinforcement learning, candidate-coverage analysis, and policy evaluation.

## Get started

Clone the paper hub and all three agent repositories:

```bash
git clone --recursive https://github.com/Calix-L/CardKS.git
cd CardKS
```

For an existing clone, initialize the project repositories with:

```bash
git submodule update --init --recursive
```

Start with the component that matches your research goal:

- Build and train a GuanDan agent with the [DanKS guide](https://github.com/Calix-L/DanKS#readme).
- Explore complete experimental protocols and numbers in [RESULTS.md](RESULTS.md).
- Inspect human trajectories in the [KSCB data guide](./KSCB/README.md).
- Follow the shared simulation platform in [KSPlay](./KSPlay/README.md).

## Citation

Use GitHub's **Cite this repository** action or the project [`CITATION.cff`](CITATION.cff) to cite CardKS. Publication metadata will be updated there with the paper record.

## License

CardKS code and documentation are available under the [Apache License 2.0](LICENSE). Component repositories and datasets carry their own release terms.
