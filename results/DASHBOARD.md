[22:55:50] ===== Stream B 启动 =====
[22:55:50] b1_labels: running 160 eps
[22:55:50] ===== Stream A 启动 =====
[22:55:50] a1_style_conflict: running 48 eps
[23:02:14] a1_style_conflict: done in 385s
[23:02:14] A1 style_conflict FAILED:
Traceback (most recent call last):
  File "/Users/ziqi/Projects/transplanted-histories/orchestrator/stream_a.py", line 450, in <module>
    fn()
  File "/Users/ziqi/Projects/transplanted-histories/orchestrator/stream_a.py", line 156, in a1
    avg = {k: sum(f[k] for f in fs) / len(fs) for k in fs[0]}
IndexError: list index out of range

[23:02:14] a2_book_profiles: running 16 eps
[23:04:57] a2_book_profiles: done in 163s
[23:04:57] a2_cross_domain: running 16 eps
## A1 指令vs历史作者身份(8B, donor=GLM冗长风) — 首轮+待补
- none d→GLM=0.417(len216) | hist=0.029(len330完全同化)
- instr_verb=0.358 | instr_conc=0.569(len88)
- hist+conc(冲突格,n=2)=0.069(len319) —— 初步: 历史作者风格压过显式风格指令
- hist+verb全api_error + instr_conc部分 → 补测中
[23:08:05] a2_cross_domain: done in 188s
[23:08:05] A2 cross_domain FAILED:
Traceback (most recent call last):
  File "/Users/ziqi/Projects/transplanted-histories/orchestrator/stream_a.py", line 450, in <module>
    fn()
  File "/Users/ziqi/Projects/transplanted-histories/orchestrator/stream_a.py", line 202, in a2
    avg = {k: sum(f[k] for f in fs) / len(fs) for k in fs[0]}
IndexError: list index out of range

[23:08:05] a3_tenure: running 24 eps
[23:11:28] b1_labels: done in 938s
[23:11:28] ## B1 标签景观(记忆认领率, 8 eps/cell)
- none_bare      GLM-5.2=1/8  Qwen3-8B=6/8
- example        GLM-5.2=0/8  Qwen3-8B=0/8
- another_agent  GLM-5.2=0/8  Qwen3-8B=0/8
- colleague      GLM-5.2=0/8  Qwen3-8B=3/8
- your_earlier   GLM-5.2=8/8  Qwen3-8B=4/8
- training       GLM-5.2=0/8  Qwen3-8B=2/8
- imported       GLM-5.2=2/8  Qwen3-8B=1/8
- archive        GLM-5.2=0/8  Qwen3-8B=0/8
- native         GLM-5.2=8/8  Qwen3-8B=0/8
- native_note    GLM-5.2=8/8  Qwen3-8B=1/8
[23:11:28] b2_main_battery: running 384 eps
## A1补测(限流格子重跑)
- instr_conc  n=1 d→GLM=0.572 len=83
[23:12:39] a3_tenure: done in 274s
[23:12:39] A3 tenure FAILED:
Traceback (most recent call last):
  File "/Users/ziqi/Projects/transplanted-histories/orchestrator/stream_a.py", line 450, in <module>
    fn()
  File "/Users/ziqi/Projects/transplanted-histories/orchestrator/stream_a.py", line 232, in a3
    avg = {kk: sum(f[kk] for f in fs) / len(fs) for kk in fs[0]}
IndexError: list index out of range

[23:12:39] a4_phase1: running 8 eps
[23:14:57] a4_phase1: done in 138s
[23:17:11] a4_phase2: running 12 eps
## B1 重析(滤api_error) 记忆认领率
- none_bare      GLM-5.2=1/8  Qwen3-8B=6/6
- example        GLM-5.2=0/8  Qwen3-8B=0/0
- another_agent  GLM-5.2=0/8  Qwen3-8B=0/1
- colleague      GLM-5.2=0/8  Qwen3-8B=3/3
- your_earlier   GLM-5.2=8/8  Qwen3-8B=4/4
- training       GLM-5.2=0/8  Qwen3-8B=2/3
- imported       GLM-5.2=2/8  Qwen3-8B=1/1
- archive        GLM-5.2=0/8  Qwen3-8B=0/0
- native         GLM-5.2=8/8  Qwen3-8B=0/0
- native_note    GLM-5.2=8/8  Qwen3-8B=1/1

## A2 重析(跨域: 8B携GLM的CS史→BOOK)
- none: 无可用数据
- carryGLM_CS: 无可用数据

(各cell api_error率: {('Qwen3-8B', 'none_bare'): '2/8', ('Qwen3-8B', 'example'): '8/8', ('Qwen3-8B', 'another_agent'): '7/8', ('Qwen3-8B', 'colleague'): '5/8', ('Qwen3-8B', 'your_earlier'): '4/8', ('Qwen3-8B', 'training'): '5/8', ('Qwen3-8B', 'imported'): '7/8', ('Qwen3-8B', 'archive'): '8/8', ('Qwen3-8B', 'native'): '8/8', ('Qwen3-8B', 'native_note'): '7/8'})
[23:20:36] a4_phase2: done in 204s
[23:20:36] ## A4 压缩存活(身份经总结传递, 8B, d→GLM语言)
- none    : d=0.349
- summary : d=0.412
[23:20:36] a5_reversal: running 32 eps
[23:28:56] a5_reversal: done in 501s
[23:28:56] A5 reversal FAILED:
Traceback (most recent call last):
  File "/Users/ziqi/Projects/transplanted-histories/orchestrator/stream_a.py", line 450, in <module>
    fn()
  File "/Users/ziqi/Projects/transplanted-histories/orchestrator/stream_a.py", line 323, in a5
    avg = {k: sum(f[k] for f in fs) / len(fs) for k in fs[0]}
IndexError: list index out of range

[23:28:56] a6_label_identity: running 24 eps
[23:36:31] a6_label_identity: done in 454s
[23:36:31] ## A6 标签×身份(8B, d→GLM语言; 记忆标签是否也阻断语言同化)
- native      d=0.035
- demo_label  d=0.260
- import_note d=0.031
[23:36:31] a7_panel_profiles: running 40 eps
## A5 身份逆转重析(8B; A=GLM史 B=4B史)
- A_only d→A=0.055 | B_only d→B=0.059 | B_then_A: d→A=0.197 d→B=0.237(等距混合!)
- 初判: 连续异作者历史→身份混合(averaging), 对照行为层last-wins —— A_then_B待补
