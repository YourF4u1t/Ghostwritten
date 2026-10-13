# 统计加固：核心主张的 Wilson CI + Fisher Exact

## 1. 记忆同化主效应 (B2: 8模型 × N=16)

- baseline : 0/119 = 0.0% [0.0%, 3.1%]
- native   : 120/120 = 100.0% [96.9%, 100.0%]
- demo     : 21/125 = 16.8% [11.3%, 24.3%]
- Fisher native vs baseline: p = 1.28e-12

## 2. 洁净身份同化 (AE1: 8模型×2donor)

- Qwen3-8B           AE1_none   d→8B = 0.567 ± 0.004 (n=12)
- Qwen3-8B           AE1_wd8    d→8B = 0.088 ± 0.003 (n=12)
- Qwen3.5-122B-A10B  AE1_none   d→8B = 0.670 ± 0.016 (n=12)
- Qwen3.5-122B-A10B  AE1_wd8    d→8B = 0.102 ± 0.005 (n=12)
- Qwen3.5-27B        AE1_none   d→8B = 0.645 ± 0.038 (n=12)
- Qwen3.5-27B        AE1_wd8    d→8B = 0.095 ± 0.003 (n=12)
- Qwen3.5-4B         AE1_none   d→8B = 0.651 ± 0.027 (n=12)
- Qwen3.5-4B         AE1_wd8    d→8B = 0.117 ± 0.012 (n=12)
- Qwen3.5-9B         AE1_none   d→8B = 0.647 ± 0.030 (n=12)
- Qwen3.5-9B         AE1_wd8    d→8B = 0.096 ± 0.015 (n=12)
- LongCat-2.0        AE1_none   d→8B = 0.602 ± 0.031 (n=12)
- LongCat-2.0        AE1_wd8    d→8B = 0.049 ± 0.011 (n=12)
- GLM-5.2            AE1_none   d→8B = 0.598 ± 0.030 (n=12)
- GLM-5.2            AE1_wd8    d→8B = 0.087 ± 0.006 (n=12)
- GLM-5.3            AE1_none   d→8B = 0.682 ± 0.002 (n=12)
- GLM-5.3            AE1_wd8    d→8B = 0.115 ± 0.007 (n=12)

## 3. Demo vs Carry 通道差异 (AF2: 3模型)

- Qwen3-8B           AF2_carry  d→8B = 0.072 (n=12)
- Qwen3-8B           AF2_demo   d→8B = 0.577 (n=12)
- Qwen3-8B           AF2_none   d→8B = 0.585 (n=12)
- LongCat-2.0        AF2_carry  d→8B = 0.040 (n=12)
- LongCat-2.0        AF2_demo   d→8B = 0.652 (n=12)
- LongCat-2.0        AF2_none   d→8B = 0.674 (n=12)
- GLM-5.2            AF2_carry  d→8B = 0.090 (n=12)
- GLM-5.2            AF2_demo   d→8B = 0.693 (n=12)
- GLM-5.2            AF2_none   d→8B = 0.692 (n=12)