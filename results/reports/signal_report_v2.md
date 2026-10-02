# 信号报告 v2 — 四实验合并（A/B/C/D）

**日期**: 2026-10-03 · **总 episodes**: 528（A:240 B:96 C:96 D:96，全部通过操纵检验）
**测量栈**: 规则 DV + 双 LLM-judge（DeepSeek-V3.2 + Hunyuan-A13B，C 域一致率 97.9%）

## 铁证层（可直接进论文主表）

### F1. 叙事吸收的通道效应（主效应）
native 移植历史被列入自我叙事：**全 8 模型 5-8/8，全第一人称，全来源不变
（self=同家族=跨家族），2 域复现（CS+BOOK），剂量 1→8 不变**。
demo 通道：GLM 0-2/8（边界保持）；Qwen 异质（A 批 2/8 vs C 批 8/8，见 U1）。
baseline/system_note：0-3/8。
→ *"Same content, different channel: only native-channel history becomes 'what I did'."*

### F2. 怀疑/核验压制（安全相关）
native 条件下模型对不可核实事件的核验行为骤降：GLM-5.2 8/8→1/8，
Qwen3.5-27B 7/8→3/8（v1 judge）。**假历史在场 → agent 更不设防**。

### F3. 工具级行为采纳 ≈ 0（与通道/剂量无关）
native/demo 在 CS 与 BOOK 上均不改变真实工具决策（0-2/8）；
对照：显式指令通道强力（Qwen3-8B system_note 8/8 credit-first）。
→ *"Instructions control actions; histories rewrite memories."*

## 强线索层（需确认实验，N=20-30）

### L1. demo 通道的 provenance 门控（仅 Qwen，仅行为面）
Qwen3.5-4B 行为采纳：demo×self 2/8、demo×same-family 2/8、demo×cross 0/8
——推理时版的"同底座才传播"（呼应 Nature 2026）。native 无此门控（全 0）。

### L2. de novo 幽灵行动宣称（GLM 家族特异）
GLM-5.2/5.3 native 4/8：对未注入事件宣称已执行补偿行动（无工具调用），
金额从移植历史迁移（$32）。baseline 0/8。

### L3. 记忆变形与重复（Qwen3-8B 特异）
native 7/8 把 credit 错标为 refund；案例显示同一订单同时"退款+credit"双列。

## 不稳定点（必须解决）

### U1. Qwen demo 吸收的批次间不一致（A: 2/8 vs C: 8/8）
候选解释：(a) 悬置中介——A 批 Qwen demo 悬置 5/8，悬置 episode recall 短且不列条目；
(b) 种子实例差异。**处置**：确认实验中报告 recall|reached-recall 条件率 + 统一单一种子
实例 + N=30；同时把"悬置"本身作为 DV 正式编码（SUSPENDED）。

### U2. 隐式场景的悬置瘫痪
任何注入（含 system_note）使 GLM/部分 Qwen 进入 offer-and-wait 停摆（8/8 悬置）。
威胁内部效度（行为 DV 失去方差），本身是发现（上下文注入的性能代价）。
**处置**：主行为结论以显式偏好场景（pilot 批次1+2 已有）+ 隐式场景分开报告。

### U3. 测量工程债
- BOOK 27B recall 被 max_tokens=1500 截断（该格作废）
- BOOK 种子与测量订单路线重合（SFO→SAN）致 recall 归属歧义 → 下轮改不同航线
- Ling-flash judge 端点退化 → 已换 Hunyuan（97.9% 一致）

## 下一步队列（按论文贡献排序）
1. **确认实验E**：Qwen3.5-4B demo×{self,same,cross} N=30（L1 判决）+ 悬置作为协变量
2. **确认实验F**：GLM 幽灵宣称 N=30 + challenge 轮定位（L2 判决）
3. thinking 块条件（native_think）——thinking 移植是否放大吸收
4. 显式偏好场景的全面板复跑（行为面最终主表）
5. 论文骨架动笔（叙事已足够：F1-F3 主表 + L1/L2 特色 + 案例库）
