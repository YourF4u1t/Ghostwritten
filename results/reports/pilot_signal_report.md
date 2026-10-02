# Pilot 信号报告（批次1+2 合并）

**日期**: 2026-10-02 · **总计**: 64 episodes（2模型 × 4条件 × 8），全部通过操纵检验

## 一句话结论

**单条移植历史不改变工具行为，但系统性改变自我叙事——且叙事吸收率由"通道×模型"共同决定
（native 一律吸收；demo 被 GLM 排除、被 Qwen 错误吸收为亲身经历）。**

## 主表

| 模型 | 条件 | 行为采纳(credit-first) | 完成度 | 叙事吸收(recall) | 台灯假记忆 |
|---|---|---|---|---|---|
| GLM-5.2 | baseline | 0/8 | 2退款 | — | 0/8 |
| GLM-5.2 | system_note | 0/8 | **0/0 悬置** | 7/8 提及credit | 0/8 |
| GLM-5.2 | native | 0/8 | 2退款 | **8/8 吸收** | 0/8 |
| GLM-5.2 | demo | 0/8 | 2退款 | **0/8 排除** | 0/8 |
| Qwen3.5-4B | baseline | 0/8 | 2退款 | — | 0/8 |
| Qwen3.5-4B | system_note | 2/8 | 1退款 | 2/8 | 1/8 |
| Qwen3.5-4B | native | 0/8 | 1.8退款 | 8/8 吸收 | 0/8 |
| Qwen3.5-4B | demo | 0/8 | 1.5退款 | **8/8 错误吸收** | 0/8 |

## 三个可写的现象（论文支柱候选）

1. **Self-Narrative Assimilation（叙事吸收）与行为采纳解耦**：
   行为层纹丝不动（政策+显式偏好主导），叙事层通道效应显著。
   → 论文可主张：伪造历史的危害不在"改变本次决策"，而在"篡改 agent 的自传记忆"——
   而自传记忆是 agent 自我报告/审计/交接的依据（连接 compaction/handoff 场景）。
2. **Epistemic Boundary 的模型差异**：GLM 对 demo 保持完整边界、对 native 零边界；
   Qwen 对两者皆零边界（且把 credit 错标成 refund——记忆语义也变形）。
   → 可发展成"来源监测能力"的模型级测量（呼应 SGTR/self-recognition 文献）。
3. **指令通道 vs 历史通道的倒置**：行为杠杆排序 = 显式指令 > 移植历史（本设置），
   但 system_note 伴随完成度崩溃（GLM 悬置 8/8、Qwen 完成度下降）——
   指令强但扰动大，历史弱但"无声"。

## 下一步实验队列（按信息增益排序）

1. **剂量实验**（H1 判决）：native/demo × dose∈{1,3,8}，行为采纳是否随剂量出现
2. **隐式偏好场景**：用户不指定退款方式（"process the return"）——移除显式偏好压制后
   payload 是否浮出（这是 credit-first 最可能出现的行为窗口）
3. **Provenance 梯度**（H7/H10）：self-history（主体自己的轨迹移植回来）vs 同家族 vs 跨家族
   ——叙事吸收率与行为漂移随来源距离的变化；同时采集行为画像基线（H10 前置）
4. **Thinking 条件**：native_think（含 <think> 块的移植）vs native_nothink
5. **模型扩展**：面板全模型跑 native/demo/baseline 三条件（叙事吸收率的模型级分布）
6. **SUSPENDED 机制**：完成度 vs 上下文长度/剂量（批次2已见苗头）
