# Research Log — transplanted-histories

> 逆序时间轴。每个 session 从这里恢复上下文。案例阅读笔记见 results/cases/。

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
