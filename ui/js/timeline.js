import { escapeHtml as e } from "./api.js";
import { t } from "./i18n.js";
import { icon } from "./icons.js";
const tools = {
  proveit_get_research: "toolRead",
  proveit_update_research: "toolGoal",
  proveit_create_lean_code: "toolSource",
  proveit_modify_lean_code: "toolSource",
  proveit_propose_natural_proof: "toolProof",
  proveit_modify_natural_proof: "toolProof",
  proveit_verify_lean: "toolLean",
  proveit_check_candidate: "toolCandidate",
  proveit_report_blocker: "toolBlocked",
};
export function timelineEntry(item, md) {
  const key = e(item.event_key || String(item.id));
  if (item.kind === "tool")
    return `<details class="tool-event ${item.status}" data-event="${key}"><summary><span class="tool-symbol">${item.status === "running" ? '<span class="spinner"></span>' : icon(["failed", "interrupted"].includes(item.status) ? "close" : "check")}</span><span>${e(t(tools[item.tool] || "toolGeneric"))}</span><small>${e(t(item.status === "running" ? "working" : item.status === "failed" ? "failed" : item.status === "interrupted" ? "interrupted" : "toolCompleted"))}</small></summary><div class="tool-details"><code>${e(item.tool)}</code>${item.content && item.content !== "{}" ? `<pre>${e(item.content)}</pre>` : ""}</div></details>`;
  if (item.kind === "recovery")
    return `<div class="session-notice" data-event="${key}">${icon("history")}<span>${e(t("sessionRecovered"))}</span></div>`;
  return `<article class="message ${item.kind === "user" ? "user" : "assistant"}" data-event="${key}"><div class="message-label">${item.kind === "user" ? e(t("you")) : icon("model") + "Codex"}</div><div class="prose">${md(item.content)}</div></article>`;
}
export function thinking() {
  return `<div class="thinking" role="status"><span class="thinking-orbit"></span><span class="shimmer">${e(t("thinking"))}</span><span class="thinking-dots"><i></i><i></i><i></i></span></div>`;
}
