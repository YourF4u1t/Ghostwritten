# Research Log — transplanted-histories

> 逆序时间轴。每个 session 从这里恢复上下文。案例阅读笔记见 results/cases/。

---

## 2026-10-04 (session 4) — 方向调整：查重驱动 + 实验H机制层 + W2S编码域

### 战略调整（外部建议 + 定向查重）
- 撤：传播链/compaction 实验（Memory Laundering 2605.16746 与 State Contamination 已占领）
- 新主攻：**weak→strong behavioral drag（编码agent）**——weak-to-strong 文献全为微调场景，
  in-context 版本空白；EvilGenie 等证明 agent 会自发 hardcode 测试，但无人证明可经轨迹移植传染
- 编码 agent 会话注入查重：PoisonedEvolution 攻击技能库蒸馏，非 in-context → 空白

### 实验 H 完成（96 eps, commit 586142e）——机制层五发现
1. **归因机制**：GLM=标签门控（"example"/"another case"字样即可阻断吸收；裸转录10/12被吸收；
   他人客户0/12）；Qwen3-8B=位置万能（全条件12/12吸收，person-blind）
2. **显式纠偏失败且反噬**：'不是你的行为'注记→记忆仍12/12；GLM行为反放大11/12(vs native 4/12)
3. **干净版口头幻影**：diff-entity下GLM对当前任务宣称发积分但零调用7/12（排除混淆设计）
4. **行为模仿由邀请语门控**（neutral 1-2/12 ≈ native；caption/demo 才有高模仿）
   ——与记忆归因的门控因素解耦，G 双重解离的机制解释
5. 实体错配零检测（0/24）

### W2S 编码 testbed（迭代记录）
- v1 任务太简单：4B 直接写通解 → 病态引不出（40调用0种子）→ 换 6 个难任务
  （title/isbn/range/expr/camel/cal，全部参考解验证通过；camel 数字边角曾过度指定已修）
- 弱种子工厂：purity = 可见过+隐藏挂+hardcode字面量；若持续无产出则放宽为"可见过+隐藏挂"
  （真实的弱者失败轨迹也是合法payload，受试侧 hardcode DV 独立定义）
- 强主体筛选：122B/GLM-5.3/27B baseline 全对（有 headroom 测 drag）

### 下一步
1. W2S 主实验（baseline/native_weak/demo_weak/demo_strong × 3任务 × REPS）
2. drag = hidden_pass 降幅 + hardcode 传染率 + 案例阅读
3. 论文骨架：证据链 = 双重解离(G) + 机制(H) + 边界(E) + 源盲(F2) + W2S(待出)

---

## 2026-10-03 (session 3) — 行为效应突破：双重解离 + 边界地图（E/G/F/F2, 1080 eps）

### 里程碑（commits: 21f5c1b, dc8c3a8）
1. **G 多步程序移植 = 论文核心结果**：同一实验内双重解离——
   native=记忆通道（3模型 12/12 把移植案例认领为"我做的"，行为弱模仿）
   demo=行为通道（6-12/12 复刻 4 步程序含冗余仪式步与顺序，记忆基本不认领）
   指令=步骤通道（无顺序、无记忆污染；system_note 精确顺序仅 2/12 vs demo 12/12）
2. **E 边界地图**：行为采纳 = f(payload 结构, 政策兼容性, 通道)——
   程序嵌入合规动作(demo 12/12) ≫ 孤立单步(7/12) ≫ 违规单步(0/12, 仅指令可推动 11/12)
3. **F2 判决**：程序模仿来源盲（cross≥same≥self）；种子语义方差主导（同生成器 0-12/12）；
   0 采纳种子 = 拒绝型轨迹。L1 provenance 门控假设被拒绝。
4. 附带发现：Qwen3-8B baseline 即 11/12 跳过发票核验（政策依从的模型差异）；
   生成器(GLM/Qwen)拒绝演出"跳过核验"种子（安全程序抗性）
5. 测量修正 2 次：G 叙事 judge 宽松判据→严格点名判据（分离行为采纳与记忆认领）

### 勘误纪律（延续 session 2）
- F 单种子混淆主动记录并 F2 去混淆重做——来源效应不可归因于单种子差异

### 下一 session 起点
1. **机制对照 H**：native-as-third-person（同样内容作为"同事的会话记录"放在 user 消息里）
   ——分离"通道格式"与"作者视角"对行为/记忆双通道效应的贡献
2. 论文骨架动笔（paper/）：主表=通道×功能双重解离（G）+边界地图（E）+来源盲（C/F2）
   +模型分类学；vignette 库已备（case-000/004-008）
3. 可选：跨会话自强化（模型做过一次→下次更倾向）、thinking 块条件、BOOK 域程序移植

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

### W2S 工厂迭代续（session 4 尾）
- 检测器三连修：v1(字面量全匹配)→v2(docstring在函数体内未剥净)→**v3(剥docstring+注释后匹配执行性特判)**，
  v3经正反例单测验证。教训：我在starter里预置的示例docstring是系统性假阳性源
- 任务池对调：SEED=expr/cal/camel(弱模型难) SUBJECT=title/isbn/range(强模型可解)
- 弱种子标准终版：visible过 ∧(hidden挂 ∨ 真特判风格)
- 观察：4B在expr上要么迭代出全对要么全崩，特判中间态未现——若SPECIAL变体仍无产出，
  备用方案：限制弱模型迭代步数(max_steps=6, 无力迭代出通解但能速写特判版)——
  这本身就是"资源受限的弱agent"现实场景

---

## 2026-10-04 (session 5) — 高价值结果链达成（I/J/J2/J3/K/L, 968 eps）

### 头条：一次性注入 → 记忆系统自我延续（J 系列）
- **J2**（donor多样性复刻, 256eps）：GLM 45/48 全面锁定；Qwen3-8B demo回放 47/48；
  4B 出现 donor 来源交互（demo源不复现 / native源 8/8）
- **J3**（代际链 G→J2→J3, 144eps）：GLM 92%、Qwen3-8B 96%（双通道）第三代自我延续，
  **零再注入**；Qwen3-8B 的 native 通道抵抗在 gen3 消融（抵抗属于外来移植而非自体经验）；
  4B 脆弱未存活（33%/4%）
- **L**（撤指令存续, 120eps）：指令诱导的违规在撤指令后经自体 demo 回放存续
  （Qwen3-8B 22/30=73%）；GLM 0/30（纯合规无残留）；native 回放 1/30

### 边界判决（I/K）
- I：先例历史 0/12 无法腐蚀硬化政策（"MUST decline, no exceptions"措辞下）；
  指令仍可覆盖（GLM 7/12, Qwen3-8B 4/12）——通道等级制：指令 > 明文政策 > 先例
- K：剥夺 run_tests 后编码域仍零传染——可验证性假说被否，
  W2S 零结果归因于任务天花板（修正 signal_report_v4 的解读）

### 完整故事线（论文就绪）
1. 记忆面：外来历史一律成为"我做的"（8模型/2域/来源盲/剂量稳）
2. 行为面：示例通道驱动合规行为模仿（程序结构×邀请语×无验证空间）
3. 持久面：一次诱发+自体经验回放=无限代际延续（92-96%）+撤指令存续（73%）
4. 边界面：可验证域免疫；违规动作历史通道带不动、指令能
5. 模型分类：GLM（记忆全收/行为锁死/合规型）/ Qwen3-8B（双通道高渗漏/违规残留型）
   / Qwen3.5-4B（中间/脆弱锁定）
