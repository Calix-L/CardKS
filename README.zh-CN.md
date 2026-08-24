<p align="right">
  <a href="README.md">English</a> · <strong>简体中文</strong>
</p>

<h1 align="center">CardKS</h1>

<p align="center">
  <strong>面向长程决策的剩余关键结构建模</strong>
</p>

<p align="center">
  一套结构化决策框架 · 三种不完美信息卡牌游戏 · SOTA 级表现
</p>

<p align="center">
  <a href="#一篇论文三项贡献">论文贡献</a> ·
  <a href="#主要结果">主要结果</a> ·
  <a href="#cardks-如何工作">方法</a> ·
  <a href="#研究体系">研究体系</a> ·
  <a href="RESULTS.md">完整表格</a> ·
  <a href="#引用">引用</a>
</p>

<p align="center">
  <a href="LICENSE"><img alt="Apache-2.0 许可证" src="https://img.shields.io/badge/license-Apache--2.0-D22128"></a>
  <img alt="三个游戏达到 SOTA" src="https://img.shields.io/badge/SOTA-3_card_games-5865F2">
  <img alt="Top-5 专家动作召回率" src="https://img.shields.io/badge/Top--5_recall-93.09%25%E2%80%9395.00%25-1F9D72">
  <img alt="KSPlay 吞吐提升" src="https://img.shields.io/badge/KSPlay-up_to_2.10%C3%97-F59E0B">
</p>

<p align="center">
  <a href="assets/cardks-framework.webp"><img src="assets/cardks-framework.webp" alt="CardKS 的信息状态、结构化候选召回、Actor-Critic 与 PPO 自博弈框架" width="960"></a><br>
  <sub><strong>总体框架。</strong> 信息状态、结构感知召回、候选条件化 Actor-Critic 与 PPO 自博弈。</sub>
</p>

CardKS 是一个面向大规模组合动作空间与不完美信息卡牌博弈的统一长程决策框架。它基于一个关键观察：**一次动作不仅改变当前局面，也会重塑此后每一步决策的结构。**

CardKS 根据动作执行后剩余手牌保留的关键结构评价合法动作，召回紧凑且多样的 Top-K 候选集合，再由候选条件化 Actor-Critic 通过 PPO 自博弈学习依赖局面的最终选择。同一套方法分别构成掼蛋智能体 **DanKS**、斗地主智能体 **DouKS** 和 Gin Rummy 智能体 **RummyKS**。

> **召回能够保留未来选择的动作，再学习每个选择在何时产生长期价值。**

## 一篇论文，三项贡献

| **CardKS · 决策框架** | **KSCB · 人类基准** | **KSPlay · 高性能平台** |
| --- | --- | --- |
| 结构感知候选召回与候选条件化 Actor-Critic 学习 | 首个同时覆盖掼蛋与斗地主的专家级基准 | 规则即代码、并行模拟、分布式评测、自博弈与在线推理 |
| 三个游戏均达到 SOTA，Top-5 专家动作召回率达 93.09%–95.00% | 经回放验证的轨迹支持学习、评测与候选分析 | 32 环境吞吐最高提升 2.10×，完整决策保持毫秒级 |

## 主要结果

CardKS 在合作博弈、非对称身份博弈和双人博弈中均达到 SOTA 级表现。

| 游戏 | CardKS 智能体 | 代表性对手 | 直接对战结果 |
| --- | --- | --- | ---: |
| 掼蛋 | **DanKS** | DanZero | **71.50%** 大局胜率 |
| 斗地主 | **DouKS** | DouZero | **54.00%** 胜率 |
| Gin Rummy | **RummyKS** | IRumAI | **58.37%** 方法胜率 |

<p align="center">
  <a href="assets/main-results.webp"><img src="assets/main-results.webp" alt="CardKS 在掼蛋、斗地主和 Gin Rummy 上的主要实验结果" width="500"></a><br>
  <sub><strong>表 1.</strong> 各游戏配对牌局、固定种子与身份交换协议下的主要对战结果。</sub>
</p>

这些结果展示了同一方法跨越三类不同交互结构的迁移能力：

- **掼蛋：** 四人组队、隐藏手牌、队友协作与完整晋级赛结果。
- **斗地主：** 地主与农民身份非对称，并具有身份相关的策略目标。
- **Gin Rummy：** 双人序贯博弈，核心涉及组合保留、Knock 时机与终局收益。

### 性能来自哪里？

<p align="center">
  <a href="assets/ablation-results.webp"><img src="assets/ablation-results.webp" alt="CardKS 在三个游戏上的消融实验结果" width="720"></a><br>
  <sub><strong>表 2.</strong> 面对固定规则对手时的胜率。</sub>
</p>

完整 CardKS 分别领先确定性 **TopK-Top1** 选择器 **49.40**、**32.60** 和 **19.09** 个百分点。结构化召回负责集中高质量动作，学习型策略负责结合当前局面在候选动作中做出判断。

三个候选排序器在 Top-5 时保留 **93.09%–95.00%** 的专家等价动作，在 Top-10 时达到 **97.30%–100.00%**。这一紧凑决策接口既服务于 PPO 策略，也能提升语言模型的动作选择质量。

全部评测协议、逐对手结果、候选 Recall@K、语言模型实验、效率测量与实现配置见 [**RESULTS.md**](RESULTS.md)。

## CardKS 如何工作

| 阶段 | 核心操作 | 作用 |
| --- | --- | --- |
| **1 · 观察** | 编码可见手牌、公共历史、座位上下文与合法动作。 | 构建当前行动玩家的信息状态。 |
| **2 · 召回** | 执行每个动作，搜索剩余手牌的合法拆解。 | 显式表达对子、序列、花色、缺口与未来动作结构。 |
| **3 · 选择** | 联合编码状态、候选动作和剩余结构摘要。 | Actor 对紧凑 Top-K 集合排序，Critic 估计长期价值。 |
| **4 · 学习** | 使用 PPO、GAE 与在线自博弈优化候选策略。 | 为数步之后才体现收益的结构选择分配信用。 |

结构化排序器与学习型策略承担互补职责：召回阶段先构建高质量策略支持集，Actor-Critic 再根据当前信息状态动态调整候选优先级。

## 涌现的长程策略

CardKS 能够学习以短期出牌数量交换未来控制权的决策：在一个轨迹中保留大对子并于后续夺回牌权；在另一个轨迹中主动 PASS，保护唯一可以取胜的木板组合。

<p align="center">
  <a href="assets/emergent-strategies.webp"><img src="assets/emergent-strategies.webp" alt="CardKS 重新获得牌权与保护木板结构的两个策略案例" width="820"></a><br>
  <sub><strong>策略案例。</strong> 保留牌权，并保护唯一可以取胜的木板延续。</sub>
</p>

这些策略由剩余结构建模与自博弈共同产生，使模型表示与人类可以理解的长程决策直接对应。

## 研究体系

CardKS 是整套论文研究体系的统一入口：

| 项目 | 在论文中的作用 | 仓库 |
| --- | --- | --- |
| **DanKS** | 掼蛋智能体，包含三代召回与 PPO 完整实现 | [Calix-L/DanKS ↗](https://github.com/Calix-L/DanKS) |
| **DouKS** | 斗地主智能体，建模地主与农民身份策略 | [Calix-L/DouKS ↗](https://github.com/Calix-L/DouKS) |
| **RummyKS** | Gin Rummy 智能体，建模剩余组合结构 | [Calix-L/RummyKS ↗](https://github.com/Calix-L/RummyKS) |
| **KSPlay** | 通用规则、模拟、自博弈与评测平台 | [打开 KSPlay](./KSPlay) |
| **KS Card Benchmark** | 掼蛋与斗地主的人类回放验证轨迹 | [打开 KSCB](./KSCB) |
| **CardKS 实验结果** | 协议、完整表格、消融、召回与效率 | [打开 RESULTS.md](RESULTS.md) |

三个游戏智能体通过 Git submodule 连接，在 CardKS 项目树中点击目录即可进入各自的独立仓库。KSPlay 与 KSCB 作为跨游戏共享资源，直接位于论文主仓库中。

### KSPlay：跨游戏统一平台

KSPlay 统一规则执行、并行模拟、分布式策略评测、高吞吐自博弈与在线推理。在 32 个并行环境下，它在掼蛋、斗地主和 Gin Rummy 上分别达到参考环境 **1.31×**、**2.10×** 和 **1.31×** 的吞吐量；CardKS 在三个游戏中的完整决策延迟均低于 **2.26 ms**。

### KSCB：游戏规模的人类决策数据

公开的 KS Card Benchmark 目前包含 **1,305 场完整掼蛋晋级赛、覆盖 14,823 小局**，以及 **947 场完整斗地主对局**。每条轨迹使用紧凑的 JSONL 格式保存有序事件与终局结果，可用于模仿学习、离线强化学习、候选覆盖率分析和策略评测。

## 快速开始

克隆论文主仓库与三个游戏智能体：

```bash
git clone --recursive https://github.com/Calix-L/CardKS.git
cd CardKS
```

已有仓库可通过下面的命令初始化项目仓库：

```bash
git submodule update --init --recursive
```

根据研究目标选择入口：

- 通过 [DanKS 使用指南](https://github.com/Calix-L/DanKS#readme)构建和训练掼蛋智能体。
- 在 [RESULTS.md](RESULTS.md) 查看完整实验协议与数值。
- 在 [KSCB 数据指南](./KSCB/README.md)查看人类对局轨迹。
- 在 [KSPlay](./KSPlay/README.md)了解跨游戏模拟平台。

## 引用

可使用 GitHub 的 **Cite this repository** 功能或项目 [`CITATION.cff`](CITATION.cff) 引用 CardKS。论文正式发布信息将同步更新在该文件中。

## 许可证

CardKS 代码与文档采用 [Apache License 2.0](LICENSE)。各组件仓库与数据集使用各自的发布许可。
