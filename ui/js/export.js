/** Render a portable research report without changing math delimiters or source. */
export function researchMarkdown(bundle, language = "en") {
  const en = language === "en",
    pick = (zh, enText) => (en ? enText : zh);
  const p = bundle.proof,
    w = bundle.research,
    g = w.goal || {},
    last = w.checks?.at(-1);
  const fence = (text, lang = "") => {
    const runs = String(text || "").match(/`+/g) || [];
    const ticks = "`".repeat(Math.max(3, ...runs.map((x) => x.length + 1)));
    return `${ticks}${lang}\n${text || ""}\n${ticks}`;
  };
  const title = String(p.title).replace(/[\r\n]+/g, " ");
  const out = [
    `# ${title}`,
    `> ProveIt · ${pick("研究记录", "Research record")} · ${bundle.exportedAt}`,
    `> ${pick("Lean 只验证编码后的命题；自然语言含义、假设和研究价值仍需人工审阅。", "Lean checks the encoded proposition only. Meaning, assumptions and significance require human review.")}`,
  ];
  out.push(
    `## ${pick("研究目标", "Research goal")}`,
    g.natural || pick("尚未登记", "Not registered"),
  );
  out.push(
    `### ${pick("约定与假设", "Assumptions")}`,
    g.assumptions || pick("未额外说明", "Not specified"),
  );
  if (g.formalType)
    out.push(
      `### ${pick("形式化目标", "Formal target")}`,
      fence(`${g.targetName} : ${g.formalType}`, "lean"),
    );
  out.push(`## ${pick("证明路线", "Proof outline")}`);
  for (const [i, s] of (w.steps || []).entries()) {
    out.push(
      `### ${i + 1}. ${s.title}`,
      `**${pick("状态", "Status")}**: ${s.status}`,
      s.content || "",
    );
    if (s.dependsOn?.length)
      out.push(
        `**${pick("依赖", "Depends on")}**: ${s.dependsOn.map((id) => w.steps.find((x) => x.id === id)?.title || id).join(", ")}`,
      );
    if (s.leanDeclaration) out.push(fence(s.leanDeclaration, "lean"));
  }
  out.push(
    `## ${pick("自然语言证明", "Written proof")}`,
    p.natural_proof || pick("尚未整理", "Not yet written"),
  );
  out.push(`## Lean`, fence(p.source, "lean"));
  const verified = w.targetVerified && w.verificationCurrent;
  out.push(
    `## ${pick("验证与人工审阅", "Verification and review")}`,
    `- ${pick("形式目标", "Formal target")}: ${verified ? pick("已验证", "Verified") : last && !w.verificationCurrent ? pick("证据已过期", "Evidence out of date") : pick("未验证", "Not verified")}`,
    `- ${pick("目标含义与假设", "Meaning and assumptions")}: ${w.goalReviewed ? pick("已审阅", "Reviewed") : pick("待审阅", "Pending review")}`,
  );
  if (last)
    out.push(
      `- ${pick("检查时间", "Checked at")}: ${last.createdAt}`,
      `- ${pick("环境", "Environment")}: ${last.projectId}`,
      `- SHA-256: ${last.sourceHash}`,
      `- ${pick("公理依赖", "Axiom dependencies")}: ${(last.result?.axioms || []).join(", ") || pick("无记录", "None recorded")}`,
      fence(
        (last.result?.diagnostics || []).map((d) => d.message).join("\n") ||
          last.result?.stdout ||
          "",
      ),
    );
  const notes =
    typeof bundle.notes === "string" ? bundle.notes : bundle.notes?.content;
  if (notes) out.push(`## ${pick("研究备注", "Notes")}`, notes);
  out.push(`## ${pick("对话与工具记录", "Conversation and tool record")}`);
  const entries = bundle.timeline || bundle.messages || [];
  for (const item of entries) {
    const kind = item.kind || item.role;
    out.push(
      `### ${kind === "user" ? pick("研究者", "Researcher") : kind === "tool" ? pick("工具调用", "Tool call") : "Codex"}${item.tool ? " · " + item.tool : ""}`,
      `${item.created_at || ""}${item.status ? " · " + item.status : ""}`,
    );
    if (kind === "tool") out.push(fence(item.content, "json"));
    else if (kind === "recovery")
      out.push(
        pick(
          "会话占用冲突已恢复；保留本地研究与对话。",
          "Recovered a session ownership conflict; local research and conversation retained.",
        ),
      );
    else out.push(item.content || "");
  }
  return out.join("\n\n") + "\n";
}
