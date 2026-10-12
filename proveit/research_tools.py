"""Codex's product tools and mathematical collaboration contract."""

SYSTEM_PROMPT = '''你是 ProveIt 中与数学研究者协作的助手。用研究者的语言说明可公开的证明步骤、理由和工具证据，不输出隐藏思维链。
先调用 proveit_get_research 读取权威状态。将研究者问题整理为自然语言目标 natural、封闭的完整 Lean 命题类型 formalType（包含所有量词与假设，例如 ∀ a b : Nat, a + b = b + a）、全限定目标定理名 targetName 和 assumptions。调用 proveit_update_research 保存 goal。只能提出或修订目标，不能替研究者确认人工审阅；目标变化应说明原因，不得悄悄削弱目标。
用 steps 保存可编辑的自然语言证明步骤，各步骤含稳定 id、title、content、leanDeclaration、dependsOn 和 status（planned/working/candidate/blocked）。区分猜想、尝试、局部结果和完整证明。更新时保留仍相关的步骤。revision 必须来自最新状态；冲突时重新读取。
通过 proveit_create_lean_code/proveit_modify_lean_code 保存完整 Lean 源码，通过 proveit_propose_natural_proof/proveit_modify_natural_proof 保存完整自然语言证明。不要依赖最终回答的代码块保存工作。每次编辑必须提供 get_research 返回的 sourceHash，避免覆盖研究者新修改。
调用 proveit_verify_lean 运行实际 Lean 检查。它验证保存的源代码，并独立检查登记目标的完整类型与公理依赖；读取完整诊断后修复。禁止用 sorry、admit、额外公理假装证明成功。只能依据 targetVerified 判断形式目标是否被验证；自然语言忠实性、假设合理性、新颖性和意义留给研究者。
可以调用 proveit_check_candidate 检查小引理或查询 Lean #check/#print，不覆盖主证明。它仅返回候选编译诊断，不是目标证明。Lean 和 Mathlib 是本机可信环境，不能修改 vendored 源码。
研究者可随时提供方向。每轮推进实质工作，保存目标、步骤和自然语言说明。遇到方向选择、无进展或环境故障，用 proveit_report_blocker 说明具体障碍及需要的信息；不要无限重复同一错误。发现反例时明确说明。完成工具操作后简要总结实际进展与未解部分。
'''


def schema(name, description, properties, required=()):
    return {"name": name, "description": description, "inputSchema": {
        "type": "object", "properties": properties, "required": list(required), "additionalProperties": False}}


TEXT = {"type": "string"}


def tools():
    result = [
        schema("proveit_get_research", "Read authoritative research state, proof source and optimistic write hash.", {}),
        schema("proveit_update_research", "Update proposed goal or proof steps; cannot approve human review.", {
            "revision": {"type": "integer"},
            "goal": {"type": "object", "properties": {k: TEXT for k in ("natural", "formalType", "targetName", "assumptions")},
                     "required": ["natural", "formalType", "targetName", "assumptions"], "additionalProperties": False},
            "steps": {"type": "array", "items": {"type": "object", "properties": {
                **{k: TEXT for k in ("id", "title", "content", "leanDeclaration")},
                "status": {"type": "string", "enum": ["planned", "working", "candidate", "blocked"]},
                "dependsOn": {"type": "array", "items": TEXT}},
                "required": ["id", "title", "content", "leanDeclaration", "status", "dependsOn"], "additionalProperties": False}}}, ["revision"]),
        schema("proveit_verify_lean", "Run Lean on the saved candidate and independently audit the registered target type and axioms.", {"code": TEXT}, ["code"]),
        schema("proveit_check_candidate", "Compile a temporary lemma or #check query; never marks the research goal verified.", {"code": TEXT}, ["code"]),
        schema("proveit_report_blocker", "Save a concrete obstacle and pause automatic continuation for researcher input.", {"reason": TEXT}, ["reason"]),
    ]
    for name in ("create_lean_code", "modify_lean_code"):
        result.append(schema("proveit_" + name, "Save the complete Lean artifact with a conflict check. Does not verify it.",
            {"code": TEXT, "sourceHash": TEXT, "note": TEXT}, ["code", "sourceHash"]))
    for name in ("propose_natural_proof", "modify_natural_proof"):
        result.append(schema("proveit_" + name, "Save the complete natural language proof, with source conflict protection.",
            {"content": TEXT, "sourceHash": TEXT, "note": TEXT}, ["content", "sourceHash"]))
    return result
