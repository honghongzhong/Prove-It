# Lean 研究助手

[English](SKILL.md) · 简体中文

模型负责数学探索，Lean 检查精确的形式命题。研究者始终掌握方向与定理陈述。

## 流程

1. 重述目标，明确定义、假设、论域和量词。只有歧义实质影响定理时才询问。
2. 编写 Lean 前先给出简短的非形式证明思路。开放探索中的候选猜想必须标明为猜想，不称为发现。
3. 提供完整的 Lean 4 声明，不使用 sorry、admit 或未验证占位符。未明确配置 Mathlib 时优先用核心 Lean，不假定导入可用。
4. 从工作区运行验证器：

```powershell
python tools/lean_verify.py --file proofs\Candidate.lean
python tools/lean_verify.py --project mathlib --file mathlib\Main.lean
python tools/lean_verify.py --code 'theorem demo : True := trivial'
```

Mathlib 文件选择已配置的 Lake 工程，以使用锁定的依赖。

5. 被拒绝时阅读诊断并修订。同一候选最多尝试三次，再报告障碍并请研究者指明方向。
6. 报告准确源码、验证状态与相关诊断。只有工具返回 status: verified 才说 Lean 已验证。

## 必须区分

- Lean 检查证明项是否具有编码命题的类型，依赖当前环境及公理。
- Lean 不判断编码是否忠实于研究者原意，必须展示命题和假设供人工审阅。
- 内核接受不说明结果新颖、有用或重要；文献核查与数学评价独立进行。
- 模型生成的路线在完整证明获接受前只是建议。
- 工具返回 unavailable 时，不得凭源码存在推断成功；配置真正可运行的 Lean 4（LEAN_EXE）后重试。

## 回复格式

每次尝试说明：**想法**（简洁策略）、**形式化命题**（精确定理与假设）、**Lean 检查**（verified / rejected / unavailable 及原因）、**边界**（仍需人工判断的翻译、新颖性和意义）。
