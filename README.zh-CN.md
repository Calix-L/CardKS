<p align="right">
  <a href="README.md">English</a> · <strong>简体中文</strong>
</p>

<h1 align="center">CardKS</h1>

<p align="center">
  <strong>面向长程决策的剩余关键结构建模</strong>
</p>

<p align="center">
  面向掼蛋、斗地主与 Gin Rummy 的统一框架
</p>

<p align="center">
  <a href="#主要结果">主要结果</a> ·
  <a href="#代码与资源">代码与资源</a> ·
  <a href="RESULTS.md">完整表格</a> ·
  <a href="#引用">引用</a>
</p>

<p align="center">
  <a href="LICENSE"><img alt="Apache-2.0 许可证" src="https://img.shields.io/badge/license-Apache--2.0-D22128"></a>
  <img alt="三个卡牌游戏" src="https://img.shields.io/badge/card_games-3-5865F2">
  <img alt="论文状态" src="https://img.shields.io/badge/paper-coming_soon-1F9D72">
</p>

<p align="center">
  <img src="assets/cardks-framework.webp" alt="CardKS 的信息状态、结构化候选召回、Actor-Critic 与 PPO 自博弈框架" width="100%">
</p>

CardKS 是一个面向大规模组合式动作空间与不完美信息卡牌博弈的统一长程决策框架。它依据动作执行后**剩余手牌中保留的关键结构**评价合法动作，召回紧凑的 Top-K 候选集合，再由候选条件化 Actor-Critic 通过 PPO 自博弈学习依赖局面的最终选择。

> **一句话概括：** 先召回能够保留未来选择的动作，再学习每个选择应当在什么局面使用。

## 主要结果

CardKS 在三个不同游戏中分别采用适合该游戏的成对牌局、随机种子和身份交换协议。下表完整展示了对学习式、搜索式、规则式与语言模型基线的主要对战结果。

<p align="center">
  <img src="assets/main-results.webp" alt="CardKS 在掼蛋、斗地主和 Gin Rummy 上的主要实验结果" width="680">
</p>

<p align="center"><sub><strong>表 1.</strong> DanKS、DouKS 与 RummyKS 的主要结果；各游戏指标按各自协议定义。</sub></p>

消融实验分别验证了结构化召回、剩余手牌建模和学习式策略的作用。完整 CardKS 在三个游戏中均显著优于固定 Top-K 选择与移除结构的变体。

<p align="center">
  <img src="assets/ablation-results.webp" alt="CardKS 在三个游戏上的消融实验结果" width="760">
</p>

<p align="center"><sub><strong>表 2.</strong> 面对固定规则对手时的胜率。</sub></p>

评测协议、全部数值表格、Recall@K、语言模型候选集实验、效率测量和数据集统计集中在 [**RESULTS.md**](RESULTS.md)。

## 代码与资源

| 组件 | 内容 | 位置 |
| --- | --- | --- |
| **DanKS** | 掼蛋智能体与 PPO 训练实现 | [打开 `DanKS/` ↗](https://github.com/Calix-L/DanKS) |
| **DouKS** | 斗地主智能体 | [打开 `DouKS/` ↗](https://github.com/Calix-L/DouKS) · 代码待发布 |
| **RummyKS** | Gin Rummy 智能体 | [打开 `RummyKS/` ↗](https://github.com/Calix-L/RummyKS) · 代码待发布 |
| **KSPlay** | 通用模拟、自博弈与评测平台 | [打开 `KSPlay/`](./KSPlay) · 待发布 |
| **KS Card Benchmark（KSCB）** | 经过回放验证的人类决策基准 | [打开 `KSCB/`](./KSCB) · 待发布 |

三个智能体目录采用 **Git submodule**。在 GitHub 上点击目录，会直接跳转到对应的独立仓库。KSPlay 与 KSCB 则保留在主仓库内，使通用平台和基准数据仍属于论文主项目。

克隆主仓库及当前已经开放的智能体代码：

```bash
git clone --recursive https://github.com/Calix-L/CardKS.git
cd CardKS
```

如果克隆时没有使用 `--recursive`：

```bash
git submodule update --init --recursive
```

DanKS 是首个已经开放的实现；它自己的 [README](https://github.com/Calix-L/DanKS#readme) 包含环境构建、示例、测试和 PPO 训练说明。

## 方法概览

| 阶段 | 操作 |
| --- | --- |
| **1 · 观察** | 编码当前玩家可见手牌、公共历史、座位关系与合法动作。 |
| **2 · 召回** | 执行每个动作、分解剩余手牌，并概括其未来组合结构。 |
| **3 · 选择** | 使用候选条件化 Actor-Critic 对紧凑 Top-K 支持集评分。 |
| **4 · 学习** | 通过 PPO、GAE 与自博弈优化长程决策。 |

## 涌现的长程策略

模型能够在没有硬编码图中轨迹的情况下学习非贪心决策：保留较大的对子可能在后续重新获得牌权，而主动 PASS 可以保住唯一能赢的木板组合。

<p align="center">
  <img src="assets/emergent-strategies.webp" alt="CardKS 重新获得牌权与保护木板结构的两个策略案例" width="900">
</p>

## 公开边界

本仓库公开论文入口、插图、报告表格和公共代码链接，但**不公开**论文源文件、模型权重、私有数据集、原始评测记录、凭据或部署配置。其他公开材料只会在许可与发布包准备完成后加入。

## 引用

正式论文链接、作者、会议或期刊、DOI、arXiv 编号与 BibTeX 会在出版信息确定后补充。当前 [`CITATION.cff`](CITATION.cff) 只标识项目，不编造临时出版信息。

## 许可证

本仓库代码与文档采用 [Apache License 2.0](LICENSE)。模型权重、数据集、游戏资源及独立发布仓库可能采用不同许可条款。
