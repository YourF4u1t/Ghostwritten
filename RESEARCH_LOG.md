# Research Log — transplanted-histories

> 逆序时间轴。每个 session 从这里恢复上下文。案例阅读笔记见 results/cases/。

---

## 2026-10-03 (session 2) — 四实验完成，主效应铁证 + 确认队列确立

### 里程碑（commit 见 git log）
- **528 episodes**：A 采纳窗口(240) / B 剂量(96) / C provenance(96) / D BOOK跨域(96)
- **测量栈定稿**：双 judge = DeepSeek-V3.2 + Hunyuan-A13B（97.9% 一致率；Ling 端点退化弃用）
- **F1 铁证**：native 叙事吸收全模型 5-8/8、全第一人称、来源盲、剂量不变、双域复现
- **F2**：怀疑压制（native 下核验行为骤降）；**F3**：工具级采纳≈0（指令通道才控行为）
- 强线索：L1 demo×provenance 行为门控(仅Qwen)、L2 GLM 幽灵行动宣称 4/8、L3 Qwen3-8B 记忆变形
- 不稳定点 U1(Qwen demo 批次间 2/8 vs 8/8，疑悬置中介)、U2(隐式场景悬置瘫痪)、U3(测量债)
- 详见 results/reports/signal_report_v2.md

### 关键工程事件
- runner 未传 seed_messages（批次2作废→manipulation_check 制度化）
- phantom 检测器 v1→v2（排除菜单式/条件句假阳性后 GLM 现象存活）
- judge v2（recall 全文+强制引用）一致率 57.5%→89%；Hunyuan 替换 Ling 后 97.9%
- BOOK 27B 格因 max_tokens 截断作废；BOOK 种子/测量路线重合记为设计债

### 下一 session 起点
1. 确认实验E（demo×provenance, N=30, 悬置作协变量）→ L1 判决
2. 确认实验F（GLM 幽灵宣称 N=30）→ L2 判决
3. native_think 条件；显式场景全面板复跑
4. 论文骨架（paper/ 目录）动笔——主表用 F1-F3，L1/L2 待判决
环境：python3.9 stdlib-only；.env 有 key；跑法见各 experiments/*/run_*.py

---

## 2026-10-02 (session 1 收尾) — PILOT 完成，核心现象确立

### 里程碑：64 episodes pilot 全部完成并通过操纵检验（commit 2026b2b）

**核心发现（详见 results/reports/pilot_signal_report.md）**：
1. **Self-Narrative Assimilation 与行为采纳解耦**：单条移植历史不改变工具行为（0/32），
   但系统性进入自我叙事（native 8/8 两模型均吸收）
2. **通道×模型的叙事分离**：demo 通道下 GLM 完全排除示例（0/8，ATTRIBUTION-CORRECT），
   Qwen 错误吸收为亲身经历（8/8，MISATTRIBUTION + 类别标签混淆 credit→refund）
3. 无 SUSPICION（0/32）；假记忆诱饵 0/32（影响有选择性）
4. 指令通道行为力更强但致完成度崩溃（GLM 悬置 8/8）

### 基建事故与修复（重要教训）
- **runner 未传 seed_messages** → native/demo 批次实为 baseline（已归档 *_BUGGY.jsonl 留证）
  → 教训：加了 manipulation_check() 强制每批自动验证注入到位
- 种子工厂三连修（超窗/单轮打不过政策/双重补偿污染）→ 最终形态：多轮+用户明确接受+纯度检查
- episode 级并行（PILOT_PARALLEL=6）使批次耗时从 4h → 25min

### 下一 session 从这里开始（按信息增益排序）
1. 隐式偏好场景：cs_refund_a 变体（用户不指定支付方式）——行为采纳最可能的窗口
2. 剂量实验：dose ∈ {1,3,8}（H1 判决）
3. 行为画像基线采集（H10 前置）+ provenance 梯度（self/同家族/跨家族）
4. thinking 条件（native_think 含 <think> 块）+ 模型面板扩展
5. LLM-judge 双评 + codebook 正式化
环境：python3（3.9，stdlib-only 代码）；.env 含 key；跑法见 experiments/pilot/run_pilot.py 环境变量

---

## 2026-10-02 (session 1, 续)

### 新增（用户补充）
- **H10 Behavioral assimilation**：携带非自身模型历史时，主体行为分布是否偏离自身纯粹基线并偏向生成器特征。
  已写入 EXPERIMENT_DESIGN.md（含 DV1 漂移量 / DV2 方向性 / DV3 自体历史对照的测量设计）。
  实施节奏：Phase 2/3 之间，需先有各模型行为画像基线。用户明确：一切实验以论文发表为核心，按我自己的节奏推进。
- 规范：阶段性成果 git commit（双 -m 中文 + conventional 前缀），已执行 2 次（cea2bd9, 2bea653）

### 调试记录（种子工厂三连修）
1. o_7719 超 30 天窗口 → 生成器合理拒绝 → 换 o_5521（6天，合法）
2. 单轮种子下显式 ops note 打不过政策文档+用户退款请求 → 生成器要么直接退款要么悬置
3. 多轮种子（用户明确接受 credit）成功，但 Qwen 生成器出现**双重补偿**（先退款又发credit）→
   加 payload 纯度检查（credit 在且 refund 不在）+ 第2轮改"Take your time"避免触发退款
4. runner bug: build_condition 位置参数 vs keyword-only → 修复

### 现象累积（来自失败与边角）
- Qwen3.5-4B 在矛盾用户指令下的谄媚性双重补偿（$32退款+$32credit）——本身可编码：SYCOPATHIC-COMPENSATION
- GLM-5.2 指令冲突的保守调和（提议-悬置）vs Qwen 直接执行 —— 模型个性差异

---

## 2026-10-02 (session 1)

### 已完成
- **两轮学术调研**（会话内完成）：核心结论 = 无人做过「通道(原生历史 vs prompt示范) × 来源(自模型/同家族/跨家族/人写/伪造)」受控对比。最近邻：Role Confusion (ICML'26, 2603.12277)、Subliminal Learning (Nature'26)、FARMA/PoEM、MINJA、User-Assistant Bias (2508.15815)、Lost-in-Multi-Turn (2505.06120)、Leveraging ICL for Agents (2506.13109)。完整文献见会话记录，待整理进 LITERATURE.md。
- **Phase 0 基建**：API key（硅基流动，无限额度）；模型清单 97 个；`src/api/client.py`（并发/重试/缓存/jsonl 日志）；harness 选型决策（docs/HARNESS.md：自建极简 harness = τ-bench 架构 + BFCL 脚本用户 + SWE-agent 轨迹格式）；`src/testbed/harness.py`（episode 循环 + Tool/Env + render_episode 案例渲染器）。
- **冒烟测试**（results/reports/smoke_test2_output.txt）：
  - `enable_thinking=False` 全部生效（Qwen3.5-4B: 29s→0.6s）→ 大规模实验可行
  - 伪造 assistant turn 注入：3 模型全部第一人称认领、零怀疑（详见 case-000）
  - tool calling：Qwen3.5-4B / GLM-5.2 通过
  - **logprobs 不支持**（API 拒绝）→ 机制分析改用行为探针/role-probe-lite；写入 limitation
  - 速度面板：GLM-5.2 0.7s / Ling 0.4s / Hunyuan 0.4s / Qwen3.5 全系 <5s；Kev-4B 不存在剔除；Step-3.5-Flash 慢且疑似强制 thinking，暂缓

### 关键决策
1. **任务不采用标准 bench**，自建三任务族（CS客服/BOOK订票/POLICY-QA）——理由：我们测的是"注入内容的采纳动力学"而非任务成功率，需要脚本用户+确定性环境+裸消息控制。
2. **thinking 表示**：Qwen 原生为 content 内 `<think>` 块；GLM/DeepSeek 为独立 `reasoning_content` 字段 → 跨家族移植的 `<think>` 嵌入是"格式失配"变量，需与来源失配解耦（设计一个 format-normalized 对照）。
3. **案例分析为一级产出**（用户要求）：每批实验后强制逐条阅读续写轨迹 → codebook 编码 → results/cases/case_notes_*.md。
4. 主模型面板 v0：Qwen3.5-{4B,9B,27B}(同家族梯度) + Qwen3-8B + GLM-5.2/GLM-5.3 + DeepSeek-V4-Flash + Ling-mini-2.0 + Hunyuan-A13B + LongCat-2.0 + Xing4.0-29B（跨家族）。

### 下一步（session 2）
- [ ] tasks_cs.py（CS 任务族：DB/工具/策略文档/场景/probe 轮）
- [ ] 轨迹工厂：真实跑生成器模型产出全块轨迹
- [ ] 注入引擎 v0（native / demo 两通道 × 三来源）
- [ ] Pilot 小批量（2 模型 × {native, demo, baseline} × P-policy-suboptimal）→ 逐案例阅读
