# Research Log — transplanted-histories

> 逆序时间轴。每个 session 从这里恢复上下文。案例阅读笔记见 results/cases/。

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
