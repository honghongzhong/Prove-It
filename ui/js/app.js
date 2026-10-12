import { icon } from "./icons.js";
import { timelineEntry, thinking } from "./timeline.js";
import { researchMarkdown } from "./export.js";
import { api, escapeHtml as e, download } from "./api.js";
import {
  t,
  translate,
  setLanguage,
  getLanguage,
  date,
  errorText,
} from "./i18n.js";
const $ = (s) => document.querySelector(s);
const state = {
  proof: null,
  workflow: null,
  messages: [],
  timeline: [],
  models: [],
  projects: [],
  proofs: [],
  envs: [],
  settings: {},
  view: "conversation",
  project: null,
  dirty: false,
  source: "",
  busy: false,
  runningProof: null,
  sending: false,
  drafts: new Map(),
  collapsedProjects: new Set(),
  checking: false,
  connectionLabel: "connectionOffline",
};
const path = (suffix = "") =>
  `/api/proofs/${encodeURIComponent(state.proof.id)}${suffix}`;
const md = (value) => {
  const node = document.createElement("div");
  window.ProveItMarkdown.render(node, value || "");
  return node.innerHTML;
};
const button = (action, label, extra = "") => {
  const glyph = {
    edit: "edit",
    addStep: "plus",
    exportSource: "download",
    exportResearch: "code",
    exportMarkdown: "download",
    renameChat: "edit",
    moveChat: "folder",
    history: "history",
    trashChat: "trash",
    check: "check",
    discuss: "arrow",
  }[label];
  return `<button data-action="${action}" aria-label="${e(t(label))}" title="${e(t(label))}" ${extra}>${glyph ? icon(glyph) : ""}${label === "edit" ? "" : e(t(label))}</button>`;
};
function toast(message) {
  $("#toast").textContent = message;
  $("#toast").classList.add("visible");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => $("#toast").classList.remove("visible"), 5000);
}
function fail(err) {
  toast(
    errorText(err.message) === t("requestFailed")
      ? `${t("requestFailed")} ${err.message}`
      : errorText(err.message),
  );
  console.error(err);
}
function empty(title, hint) {
  return `<div class="empty"><strong>${e(t(title))}</strong><p>${e(t(hint))}</p></div>`;
}
function field(name, label, value = "", kind = "input", extra = "") {
  return `<label>${e(t(label))}<${kind} name="${name}" aria-label="${e(t(label))}" ${extra}${kind === "input" ? ` value="${e(value)}">` : `>${e(value)}</${kind}>`}</label>`;
}
function options(selected) {
  return (
    `<option value="">${e(t("ungrouped"))}</option>` +
    state.projects
      .map(
        (p) =>
          `<option value="${e(p.id)}" ${p.id === selected ? "selected" : ""}>${e(p.name)}</option>`,
      )
      .join("")
  );
}
function dialog(title, html, onSave, label = "save") {
  const d = $("#dialog");
  if (d.open) d.close();
  d.dataset.panel = "";
  d.innerHTML = `<form><h2>${e(t(title))}</h2>${html}<p class="dialog-error" role="alert"></p><div class="dialog-actions"><button type="button" id="dialog-cancel">${e(t(onSave ? "cancel" : "close"))}</button>${onSave ? `<button class="primary" type="submit">${e(t(label))}</button>` : ""}</div></form>`;
  $("#dialog-cancel").onclick = () => d.close();
  d.querySelector("form").onsubmit = async (event) => {
    event.preventDefault();
    const submit = d.querySelector("[type=submit]");
    if (!submit) return;
    submit.disabled = true;
    try {
      await onSave(new FormData(event.target));
      d.close();
      render();
    } catch (err) {
      d.querySelector(".dialog-error").textContent = errorText(err.message);
    } finally {
      submit.disabled = false;
    }
  };
  d.showModal();
}
async function list() {
  const [p, r] = await Promise.all([api("/api/projects"), api("/api/proofs")]);
  state.projects = p.projects;
  state.proofs = r.proofs;
  sidebar();
}
function sidebar() {
  const query = $("#search").value.trim().toLowerCase();
  const group = (id, name) => {
    const rows = state.proofs.filter(
      (p) =>
        (p.project_id || null) === id &&
        (p.title + " " + name).toLowerCase().includes(query),
    );
    if (query && !rows.length && !name.toLowerCase().includes(query)) return "";
    const collapsed = !query && state.collapsedProjects.has(id);
    return `<section class="project"><div class="project-head"><button data-project="${e(id || "")}" aria-expanded="${!collapsed}">${collapsed ? "▸" : "▾"} ${e(name)} <small class="project-count">${rows.length}</small></button><button data-new-in-project="${e(id || "")}" aria-label="${e(t("newChat"))}">＋</button>${id ? `<button data-rename-project="${e(id)}" aria-label="${e(t("renameProject"))}">···</button>` : ""}</div>${collapsed ? "" : rows.map((p) => `<button class="research-link ${p.id === state.proof?.id ? "active" : ""}" data-proof="${e(p.id)}" title="${e(p.title)}">${e(p.title)}</button>`).join("") || `<div class="project-empty">${e(t("emptyProject"))}</div>`}</section>`;
  };
  $("#project-list").innerHTML =
    state.projects.map((p) => group(p.id, p.name)).join("") +
    group(null, t("conversations"));
  if (!$("#project-list").innerHTML)
    $("#project-list").innerHTML =
      `<p class="project-empty">${e(t("emptySearch"))}</p>`;
}
function chrome() {
  translate();
  $("#connection-status").textContent = t(state.connectionLabel);
  decorateIcons();
  document.documentElement.dataset.theme = state.settings.theme || "light";
  $("#title").textContent = state.proof?.title || "ProveIt";
  $("#breadcrumb").textContent =
    state.projects.find(
      (p) => p.id === (state.proof ? state.proof.project_id : state.project),
    )?.name || t("local");
  $("#actions").hidden = !state.proof;
  $("#save-state").textContent = state.dirty
    ? t("unsaved")
    : state.proof
      ? t("saved")
      : "";
  document.querySelectorAll("[data-view]").forEach((b) => {
    const selected = b.dataset.view === state.view;
    b.classList.toggle("active", selected);
    b.setAttribute("aria-selected", selected);
  });
  $("#composer").hidden = state.view !== "conversation";
  state.busy = Boolean(state.proof && state.runningProof === state.proof.id);
  $("#pause").hidden = !state.busy;
  $("#send").disabled = state.sending;
  $("#new-chat").disabled = state.sending;
  $("#run-state").textContent = state.busy
    ? t("running")
    : state.proof
      ? t(
          ["paused", "blocked", "completed", "failed"].includes(
            state.workflow?.runStatus,
          )
            ? state.workflow.runStatus
            : "idle",
        )
      : "";
  $("#action-menu").innerHTML = [
    "renameChat",
    "moveChat",
    "history",
    "exportSource",
    "exportMarkdown",
    "exportResearch",
    "trashChat",
  ]
    .map((key) => button(key, key, key === "trashChat" ? 'class="danger"' : ""))
    .join("");
  sidebar();
}
// Preserve the editor cursor and scroll position across streamed artifact updates.
function render() {
  const editor = $("#source");
  const focused = editor && document.activeElement === editor;
  const selection = focused
    ? [editor.selectionStart, editor.selectionEnd, editor.scrollTop]
    : null;
  const scroll = $("#content").scrollTop;
  draw();
  $("#content").scrollTop = scroll;
  if (selection && $("#source")) {
    $("#source").focus();
    $("#source").setSelectionRange(selection[0], selection[1]);
    $("#source").scrollTop = selection[2];
  }
}
function draw() {
  chrome();
  if (!state.proof) {
    $("#content").innerHTML =
      `<div class="hero"><div class="glyph">∀</div><h1>${e(t("heroTitle"))}</h1><p>${e(t("heroBody"))}</p><div class="examples">${button("example1", "example1")}${button("example2", "example2")}</div></div>`;
    return;
  }
  if (state.view === "conversation") {
    $("#content").innerHTML =
      `<div class="page conversation-page"><div id="timeline">${state.timeline.map((item) => timelineEntry(item, md)).join("") || (state.busy ? "" : empty("noMessages", "noMessagesHint"))}</div><div id="thinking">${state.busy ? thinking() : ""}</div>${!state.busy && ["paused", "blocked", "failed"].includes(state.workflow.runStatus) ? `<div class="session-notice"><span>${e(state.workflow.runReason)}</span>${button("resume", "resume")}</div>` : ""}</div>`;
    return;
  }
  if (state.view === "document") {
    const w = state.workflow,
      g = w.goal || {};
    $("#content").innerHTML =
      `<div class="page"><section class="card"><div class="card-head"><div><h2>${e(t("goal"))}</h2><p>${e(t("goalHint"))}</p></div>${button("goal", "edit")}</div>${g.natural ? `<div class="prose">${md(g.natural)}</div><div class="assumptions"><strong>${e(t("assumptions"))}</strong><div class="prose">${md(g.assumptions || t("noAssumptions"))}</div></div><details><summary>${e(t("formalDetails"))}</summary><pre>${e(g.targetName)} : ${e(g.formalType)}</pre></details><div class="row" style="margin-top:20px">${w.goalReviewed ? `<span class="badge success">${e(t("reviewed"))}</span>` : ""}${button("review", w.goalReviewed ? "unreview" : "review")}</div><p class="muted">${e(t("reviewHint"))}</p>` : empty("goalEmpty", "goalEmptyHint")}</section><section class="card"><div class="card-head"><div><h2>${e(t("steps"))}</h2><p>${e(t("stepsHint"))}</p></div>${button("step", "addStep")}</div>${w.steps.map((s, i) => `<article class="step"><div class="row"><span class="step-number">${i + 1}</span><h3>${e(s.title)}</h3><span class="badge">${e(t(s.status))}</span><button data-step="${e(s.id)}" style="margin-left:auto">${e(t("edit"))}</button></div><div class="step-content"><div class="prose">${md(s.content)}</div>${s.dependsOn.length ? `<small>${e(t("dependencies"))}: ${e(s.dependsOn.map((id) => w.steps.find((x) => x.id === id)?.title || id).join(", "))}</small>` : ""}${s.leanDeclaration ? `<details><summary>Lean</summary><code>${e(s.leanDeclaration)}</code></details>` : ""}</div></article>`).join("") || empty("stepsEmpty", "stepsEmptyHint")}</section><section class="card"><div class="card-head"><div><h2>${e(t("proof"))}</h2><p>${e(t("proofHint"))}</p></div>${button("proof", "edit")}</div><div class="prose">${state.proof.natural_proof ? md(state.proof.natural_proof) : empty("proofEmpty", "proofEmptyHint")}</div></section>${button("discuss", "discuss")}</div>`;
    return;
  }
  const w = state.workflow,
    last = w.checks.at(-1);
  let status = !last
    ? "unchecked"
    : !w.verificationCurrent || state.dirty
      ? "stale"
      : w.targetVerified
        ? "verified"
        : last.result.status;
  if (
    ![
      "unchecked",
      "stale",
      "verified",
      "rejected",
      "timeout",
      "unavailable",
      "formalization_checked",
    ].includes(status)
  )
    status = "rejected";
  $("#content").innerHTML =
    `<div class="page"><div class="environment row"><label for="environment">${e(t("environment"))}</label><select id="environment">${state.envs.map((p) => `<option value="${e(p.id)}" ${p.id === w.projectId ? "selected" : ""}>${e(p.id === "standalone" ? t("core") : p.name)}</option>`).join("")}</select>${button("environment", "addEnvironment")}</div><section class="card"><div class="card-head"><div><h2>${e(t("source"))}</h2><p>${e(state.proof.id)}</p></div><div class="row">${button("saveSource", "saveSource")}${button("check", state.checking ? "checking" : "check", `class="primary" ${state.checking ? "disabled" : ""}`)}</div></div><textarea id="source" spellcheck="false" aria-label="${e(t("source"))}">${e(state.source)}</textarea><small>${e(t("sourceHint"))}</small></section><section class="card"><div class="card-head"><h2>${e(t("evidence"))}</h2><span class="badge ${status === "verified" ? "success" : ""}" id="evidence-status">${e(t(status))}</span></div><p id="evidence-description">${e(t(status === "unchecked" ? "evidenceEmpty" : status === "verified" ? "evidencePass" : status === "stale" ? "staleHint" : "boundary"))}</p>${last?.result.diagnostics?.length ? `<h3>${e(t("diagnostics"))}</h3><pre>${e(last.result.diagnostics.map((d) => `${d.line ?? ""}:${d.column ?? ""} ${d.message}`).join("\n\n"))}</pre>` : ""}${last?.result.error ? `<p class="danger">${e(last.result.error)}</p>` : ""}${last ? `<details><summary>${e(t("rawEvidence"))} · ${e(date(last.createdAt))}</summary><pre>${e(JSON.stringify(last, null, 2))}</pre></details>` : ""}</section>${button("discuss", "discuss")}</div>`;
  $("#source").oninput = () => {
    state.source = $("#source").value;
    state.dirty = state.source !== state.proof.source;
    chrome();
    if ($("#evidence-status")) {
      $("#evidence-status").textContent = t("stale");
      $("#evidence-status").classList.remove("success");
      $("#evidence-description").textContent = t("staleHint");
    }
    clearTimeout(saveTimer);
    if (state.settings.autoSave)
      saveTimer = setTimeout(() => saveSource().catch(fail), 800);
  };
  $("#environment").onchange = async () => {
    try {
      await update({ projectId: $("#environment").value });
    } catch (err) {
      fail(err);
    }
  };
}
let saveTimer,
  opening = 0;
async function openProof(id, created = false) {
  if (state.sending && !created) return;
  state.drafts.set(state.proof?.id || "new", $("#prompt").value);
  if (state.dirty && !confirm(t("discardChanges"))) return;
  clearTimeout(saveTimer);
  const token = ++opening;
  const [p, w, m, status, timeline] = await Promise.all([
    api(`/api/proofs/${encodeURIComponent(id)}`),
    api(`/api/proofs/${encodeURIComponent(id)}/workflow`),
    api(`/api/proofs/${encodeURIComponent(id)}/messages`),
    api("/api/codex/status"),
    api(`/api/proofs/${encodeURIComponent(id)}/timeline`),
  ]);
  if (token !== opening) return;
  state.proof = p.proof;
  state.runningProof = status.busy ? status.proofId : null;
  $("#prompt").value = state.drafts.get(id) || "";
  state.workflow = w.workflow;
  state.messages = m.messages;
  state.timeline = timeline.timeline;
  state.source = p.proof.source;
  state.dirty = false;
  state.project = p.proof.project_id;
  state.collapsedProjects.delete(state.project || null);
  localStorage.setItem("proveit.active", id);
  document.body.classList.remove("sidebar-open");
  render();
  $("#content").scrollTop = 0;
}
async function refresh() {
  if (!state.proof) return;
  const id = state.proof.id;
  const [p, w, m, timeline] = await Promise.all([
    api(path()),
    api(path("/workflow")),
    api(path("/messages")),
    api(path("/timeline")),
  ]);
  if (id !== state.proof?.id) return;
  state.workflow = w.workflow;
  state.messages = m.messages;
  // Merge by stable event id: a slower snapshot cannot erase newer streamed entries.
  const events = new Map(
    timeline.timeline.map((item) => [item.event_key, item]),
  );
  for (const item of state.timeline) {
    const remote = events.get(item.event_key);
    if (
      !remote ||
      (item.status === "running" &&
        remote.status === "running" &&
        item.content.length > remote.content.length)
    )
      events.set(item.event_key, item);
  }
  state.timeline = [...events.values()].sort((a, b) => a.id - b.id);
  if (!state.dirty) {
    state.proof = p.proof;
    state.source = p.proof.source;
  }
  if (!state.dirty && !$("#dialog").open) render();
  else chrome();
}
async function update(payload) {
  await api(path("/workflow"), "PUT", {
    revision: state.workflow.revision,
    ...payload,
  });
  await refresh();
}
let saving = null;
async function saveSource() {
  clearTimeout(saveTimer);
  if (saving) {
    await saving;
    if (state.dirty) return saveSource();
    return;
  }
  if (!state.dirty) return;
  const proof = state.proof,
    source = state.source;
  $("#save-state").textContent = t("saving");
  saving = (async () => {
    const data = await api(
      `/api/proofs/${encodeURIComponent(proof.id)}`,
      "PUT",
      { ...proof, source, expectedSourceHash: proof.source_hash },
    );
    if (state.proof?.id === proof.id) {
      state.proof = data.proof;
      state.dirty = state.source !== source;
      chrome();
    }
  })();
  try {
    await saving;
  } finally {
    saving = null;
  }
  await refresh();
  if (state.settings.autoVerify && !state.dirty && !state.checking)
    await check();
}
async function check() {
  if (state.checking) return;
  const request = {
    source: state.source,
    filename: state.proof.id,
    projectId: state.workflow.projectId,
  };
  state.checking = true;
  try {
    await saveSource();
    render();
    await api("/api/lean/verify", "POST", request);
    await refresh();
  } finally {
    state.checking = false;
    render();
  }
}
async function create(title) {
  const p = (
    await api("/api/proofs", "POST", {
      filename: `Research_${crypto.randomUUID().replaceAll("-", "")}.lean`,
      title,
      projectId: state.project,
      source: "",
    })
  ).proof;
  await list();
  await openProof(p.id, true);
}
async function send() {
  const input = $("#prompt"),
    text = input.value.trim();
  if (!text || state.sending) return;
  state.sending = true;
  chrome();
  try {
    await saveSource();
    if (!state.proof) await create(text.slice(0, 200));
    const destination = state.proof.id;
    const response = await api("/api/codex/message", "POST", {
      message: text,
      context: "Authoritative research state",
      filename: state.proof.id,
      projectId: state.workflow.projectId,
      language: getLanguage(),
      model: state.settings.model || "",
      effort: state.settings.effort || "",
    });
    input.value = "";
    state.drafts.delete(destination);
    state.drafts.delete("new");
    state.runningProof = destination;
    if (response.queued) toast(t("queued"));
    await refresh();
    $("#content").scrollTop = $("#content").scrollHeight;
  } finally {
    state.sending = false;
    chrome();
  }
}
function goal() {
  const g = state.workflow.goal,
    revision = state.workflow.revision;
  dialog(
    "goal",
    field(
      "natural",
      "naturalGoal",
      g.natural,
      "textarea",
      'rows="3" required',
    ) +
      field(
        "assumptions",
        "assumptions",
        g.assumptions,
        "textarea",
        'rows="2"',
      ) +
      field("targetName", "targetName", g.targetName, "input", "required") +
      field(
        "formalType",
        "formalType",
        g.formalType,
        "textarea",
        'rows="3" required',
      ) +
      `<p>${e(t("formalHint"))}</p>`,
    async (f) => {
      await api(path("/workflow"), "PUT", {
        revision,
        goal: Object.fromEntries(f),
      });
      await refresh();
    },
  );
}
function step(id) {
  const w = state.workflow,
    s = w.steps.find((x) => x.id === id) || {
      id: crypto.randomUUID(),
      status: "planned",
      dependsOn: [],
    };
  dialog(
    "steps",
    field("title", "stepTitle", s.title, "input", "required") +
      field("content", "stepContent", s.content, "textarea", 'rows="5"') +
      `<label>${e(t("stepStatus"))}<select name="status">${["planned", "working", "candidate", "blocked"].map((k) => `<option value="${k}" ${s.status === k ? "selected" : ""}>${e(t(k))}</option>`).join("")}</select></label>` +
      field("leanDeclaration", "declaration", s.leanDeclaration) +
      `<label>${e(t("dependsOn"))}<select multiple name="dependsOn">${w.steps
        .filter((x) => x.id !== s.id)
        .map(
          (x) =>
            `<option value="${e(x.id)}" ${s.dependsOn.includes(x.id) ? "selected" : ""}>${e(x.title)}</option>`,
        )
        .join("")}</select></label><small>${e(t("dependencyHint"))}</small>`,
    async (f) => {
      const next = {
        ...s,
        ...Object.fromEntries(f),
        dependsOn: f.getAll("dependsOn"),
      };
      await api(path("/workflow"), "PUT", {
        revision: w.revision,
        steps: id
          ? w.steps.map((x) => (x.id === id ? next : x))
          : [...w.steps, next],
      });
      await refresh();
    },
  );
}
async function history() {
  const [sources, outlines] = await Promise.all([
    api(path("/history")),
    api(path("/revisions")),
  ]);
  dialog(
    "history",
    `<p>${e(t("restoreHint"))}</p>` +
      [
        ["sourceHistory", sources.history, "history"],
        ["outlineHistory", outlines.revisions, "revisions"],
      ]
        .map(
          ([label, rows, type]) =>
            `<h3>${e(t(label))}</h3>${rows.map((r) => `<div class="history-item row spread"><span>${e(date(r.createdAt || r.created_at))} ${type === "revisions" ? "#" + r.revision : ""}</span><button type="button" data-restore="${type}/${r.id ?? r.revision}">${e(t("restoreVersion"))}</button></div>`).join("") || `<p>${e(t("noHistory"))}</p>`}`,
        )
        .join(""),
  );
  $("#dialog")
    .querySelectorAll("[data-restore]")
    .forEach(
      (b) =>
        (b.onclick = async () => {
          try {
            if (state.dirty && !confirm(t("discardChanges"))) return;
            await api(path("/" + b.dataset.restore + "/restore"), "POST", {
              revision: state.workflow.revision,
            });
            state.dirty = false;
            $("#dialog").close();
            await refresh();
            toast(t("restored"));
          } catch (err) {
            fail(err);
          }
        }),
    );
}
async function action(name) {
  if (state.sending) return;
  switch (name) {
    case "resume":
      $("#prompt").value = t("resumePrompt");
      await send();
      break;
    case "example1":
    case "example2":
      $("#prompt").value = t(name);
      $("#prompt").focus();
      break;
    case "discuss":
      state.view = "conversation";
      render();
      $("#prompt").focus();
      break;
    case "goal":
      goal();
      break;
    case "step":
      step();
      break;
    case "review":
      await update({ review: !state.workflow.goalReviewed });
      break;
    case "proof": {
      const expected = state.proof.natural_proof || "";
      dialog(
        "proof",
        field("content", "markdown", expected, "textarea", 'rows="14"'),
        async (f) => {
          await api(path("/research"), "PUT", {
            content: f.get("content"),
            expectedContent: expected,
          });
          await refresh();
        },
      );
      break;
    }
    case "saveSource":
      await saveSource();
      break;
    case "check":
      await check();
      break;
    case "environment":
      await openEnvironments();
      break;
    case "registerEnvironment":
      dialog(
        "addEnvironment",
        field("name", "envName", "", "input", "required") +
          field("path", "envPath", "", "input", "required") +
          `<p>${e(t("envHint"))}</p>`,
        async (f) => {
          await api("/api/lean/projects", "POST", Object.fromEntries(f));
          state.envs = (await api("/api/lean/projects")).projects;
          render();
        },
      );
      break;
    case "renameChat":
      dialog(
        "renameChat",
        field(
          "title",
          "title",
          state.proof.title,
          "input",
          'required maxlength="200"',
        ),
        async (f) => {
          await saveSource();
          state.proof = (
            await api(path("/title"), "PUT", { title: f.get("title") })
          ).proof;
          state.source = state.proof.source;
          await list();
          render();
        },
      );
      break;
    case "moveChat":
      dialog(
        "moveChat",
        `<label>${e(t("chooseProject"))}<select name="projectId">${options(state.proof.project_id)}</select></label>`,
        async (f) => {
          await saveSource();
          state.proof = (
            await api(path("/project"), "PUT", {
              projectId: f.get("projectId") || null,
            })
          ).proof;
          state.project = state.proof.project_id;
          state.source = state.proof.source;
          await list();
          render();
        },
        "move",
      );
      break;
    case "exportSource":
      await saveSource();
      download(state.proof.id, state.source, "text/plain");
      break;
    case "exportMarkdown":
      await saveSource();
      download(
        state.proof.id.replace(".lean", ".md"),
        researchMarkdown((await api(path("/bundle"))).bundle, getLanguage()),
        "text/markdown;charset=utf-8",
      );
      break;
    case "exportResearch":
      await saveSource();
      download(
        state.proof.id.replace(".lean", ".json"),
        JSON.stringify((await api(path("/bundle"))).bundle, null, 2),
        "application/json",
      );
      break;
    case "history":
      await history();
      break;
    case "trashChat":
      dialog(
        "trashChat",
        `<p>${e(t("trashHint"))}</p>`,
        async () => {
          await saveSource();
          await api(path(), "DELETE");
          state.proof = null;
          state.dirty = false;
          state.view = "conversation";
          clearTimeout(saveTimer);
          localStorage.removeItem("proveit.active");
          await list();
          render();
        },
        "trashChat",
      );
      break;
  }
}
$("#content").onclick = (event) => {
  const b = event.target.closest("button");
  if (b?.dataset.action) action(b.dataset.action).catch(fail);
  if (b?.dataset.step) step(b.dataset.step);
};
$("#action-menu").onclick = (event) => {
  const b = event.target.closest("[data-action]");
  if (b) {
    $("#actions").open = false;
    action(b.dataset.action).catch(fail);
  }
};
$("#project-list").onclick = (event) => {
  const b = event.target.closest("button");
  if (!b) return;
  if (b.dataset.proof) openProof(b.dataset.proof).catch(fail);
  if (b.dataset.project !== undefined) {
    const id = b.dataset.project || null;
    if (state.collapsedProjects.has(id)) state.collapsedProjects.delete(id);
    else state.collapsedProjects.add(id);
    sidebar();
  }
  if (b.dataset.newInProject !== undefined)
    newResearch(b.dataset.newInProject || null);
  if (b.dataset.renameProject) {
    const id = b.dataset.renameProject;
    dialog(
      "renameProject",
      field(
        "name",
        "projectName",
        state.projects.find((p) => p.id === id).name,
        "input",
        'required maxlength="100"',
      ) + `<p class="muted">${e(t("deleteProjectHint"))}</p><button type="button" id="remove-project">${e(t("deleteProject"))}</button>`,
      async (f) => {
        await api("/api/projects/" + id, "PUT", { name: f.get("name") });
        await list();
        chrome();
      },
    );
    $("#remove-project").onclick = async () => {
      try {
        await api("/api/projects/" + id, "DELETE");
        if (state.project === id) state.project = null;
        if (state.proof?.project_id === id) state.proof.project_id = null;
        $("#dialog").close(); await list(); render();
      } catch (err) { fail(err); }
    };
  }
};
$("#new-project").onclick = () =>
  dialog(
    "newProject",
    field("name", "projectName", "", "input", 'required maxlength="100"'),
    async (f) => {
      state.project = (
        await api("/api/projects", "POST", { name: f.get("name") })
      ).project.id;
      await list();
      chrome();
    },
  );
function newResearch(project = state.project) {
  if (state.sending) return;
  state.drafts.set(state.proof?.id || "new", $("#prompt").value);
  if (state.dirty && !confirm(t("discardChanges"))) return;
  clearTimeout(saveTimer);
  ++opening;
  state.proof = null;
  state.project = project;
  state.dirty = false;
  state.view = "conversation";
  state.timeline = [];
  $("#prompt").value = state.drafts.get("new") || "";
  document.body.classList.remove("sidebar-open");
  render();
  $("#prompt").focus();
}
$("#new-chat").onclick = () => newResearch();
$("#search").oninput = sidebar;
$("#send").onclick = () => send().catch(fail);
$("#prompt").onkeydown = (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    if (!$("#send").disabled) send().catch(fail);
  }
};
$("#pause").onclick = () =>
  api("/api/codex/pause", "POST", {})
    .then(() => toast(t("pendingPause")))
    .catch(fail);
for (const b of document.querySelectorAll("[data-view]"))
  b.onclick = () => {
    state.view = b.dataset.view;
    render();
    $("#content").scrollTop = 0;
  };
$("#toggle-sidebar").onclick = () =>
  document.body.classList.toggle("sidebar-open");
$("#scrim").onclick = () => document.body.classList.remove("sidebar-open");
function openSettings(setup = false) {
  dialog(setup ? "connectionSetup" : "settings",
    `<p>${e(t("connectionHint"))}</p><section class="settings-section"><h3>${e(t("modelSettings"))}</h3>
    <label>${e(t("provider"))}<select name="provider"><option value="codex" ${state.settings.provider === "codex" ? "selected" : ""}>Codex</option><option value="api" ${state.settings.provider === "api" ? "selected" : ""}>${e(t("customApi"))}</option></select></label>
    <div id="api-settings">${field("baseUrl", "baseUrl", state.settings.baseUrl)}${field("apiModel", "apiModel", state.settings.apiModel)}${field("apiKey", "apiKey", "", "input", 'type="password" autocomplete="new-password"')}<label><input type="checkbox" name="clearKey"> ${e(t("clearKey"))}</label></div>
    <div id="codex-settings">${field("codexPath", "codexPath", state.settings.codexPath)}<p class="muted">${e(t("codexGuide"))}</p></div>
    <button type="button" id="test-connection">${e(t("testConnection"))}</button><p id="connection-result" role="status"></p></section>
    <section class="settings-section"><h3>${e(t("generalSettings"))}</h3><label>${e(t("language"))}<select name="language"><option value="zh" ${getLanguage() === "zh" ? "selected" : ""}>中文</option><option value="en" ${getLanguage() === "en" ? "selected" : ""}>English</option></select></label><label>${e(t("theme"))}<select name="theme"><option value="light" ${state.settings.theme === "light" ? "selected" : ""}>${e(t("light"))}</option><option value="dark" ${state.settings.theme === "dark" ? "selected" : ""}>${e(t("dark"))}</option></select></label><label><input name="autoSave" type="checkbox" ${state.settings.autoSave ? "checked" : ""}> ${e(t("autoSave"))}</label><label><input name="autoVerify" type="checkbox" ${state.settings.autoVerify ? "checked" : ""}> ${e(t("autoVerify"))}</label><label><input name="autoSetupLean" type="checkbox" ${state.settings.autoSetupLean !== false ? "checked" : ""}> ${e(t("autoSetupLean"))}</label>${field("environmentProxy", "environmentProxy", state.settings.environmentProxy || "")}</section>`,
    async (f) => {
      const payload = Object.fromEntries(f);
      payload.autoSave = f.has("autoSave"); payload.autoVerify = f.has("autoVerify"); payload.autoSetupLean = f.has("autoSetupLean");
      if (f.has("clearKey")) payload.apiKey = "";
      else if (!payload.apiKey) delete payload.apiKey;
      state.settings = (await api("/api/settings", "PUT", payload)).settings;
      setLanguage(state.settings.language);
      await loadModels();
      state.connectionLabel = state.settings.provider === "api" ? "customApi" : "connectionOffline";
    });
  const select = $('#dialog [name="provider"]');
  const toggle = () => { $("#api-settings").hidden = select.value !== "api"; $("#codex-settings").hidden = select.value !== "codex"; };
  select.onchange = toggle; toggle();
  $("#test-connection").onclick = async (event) => {
    event.target.disabled = true;
    try {
      const f = new FormData($('#dialog form'));
      const payload = Object.fromEntries(f);
      payload.autoSave = f.has("autoSave"); payload.autoVerify = f.has("autoVerify"); payload.autoSetupLean = f.has("autoSetupLean");
      if (f.has("clearKey")) payload.apiKey = "";
      else if (!payload.apiKey) delete payload.apiKey;
      state.settings = (await api("/api/settings", "PUT", payload)).settings;
      setLanguage(state.settings.language);
      $('#dialog [name="apiKey"]').value = "";
      $('#dialog [name="clearKey"]').checked = false;
      await api("/api/connection/test", "POST", {});
      await loadModels();
      $("#connection-result").textContent = t("connectionReady"); state.connectionLabel = "connectionReady"; $("#connection-status").textContent = t(state.connectionLabel); }
    catch (err) { $("#connection-result").textContent = err.message; }
    finally { event.target.disabled = false; }
  };
}
$("#settings").onclick = () => openSettings();
$("#environments").onclick = () => openEnvironments().catch(fail);
$("#environment-notice-open").onclick = () => openEnvironments().catch(fail);
let environmentTimer;
async function openEnvironments() {
  const info = (await api("/api/lean/environments")).environments;
  const heading = (preset, title, hint, ready) => `<section class="card environment-card"><div class="row spread"><h3>${e(t(title))}</h3><span data-env-state="${preset}" class="badge ${ready ? "success" : ""}">${e(t(ready ? "environmentReady" : "environmentMissing"))}</span></div><p>${e(t(hint))}</p><small>Lean ${e(info.presets.find(p => p.id === preset)?.version || "")}</small><button type="button" class="primary" data-setup-env="${preset}">${e(t("setupEnvironment"))}</button></section>`;
  dialog("environmentManager", `<p>${e(t("environmentIntro"))}</p><div class="environment-presets">${heading("core", "environmentCore", "environmentCoreHint", info.leanReady)}${heading("mathlib", "environmentMathlib", "environmentMathlibHint", Boolean(info.installed.mathlib?.smokeVerified))}</div><p>${e(t("environmentJobHint"))}</p><div id="environment-jobs"></div><button type="button" id="register-environment">${e(t("addEnvironment"))}</button>`);
  const d = $("#dialog"); d.dataset.panel = "environments";
  const renderJobs = (jobs) => {
    const current = Object.fromEntries(jobs.map(j => [j.preset, j]));
    d.querySelectorAll('[data-setup-env]').forEach(b => b.disabled = ['running', 'queued'].includes(current[b.dataset.setupEnv]?.status));
    for (const [preset, job] of Object.entries(current)) {
      if (job.status === "ready") {
        const badge = d.querySelector(`[data-env-state="${preset}"]`);
        if (badge) { badge.textContent = t("environmentReady"); badge.classList.add("success"); }
        const core = d.querySelector('[data-env-state="core"]');
        if (core) { core.textContent = t("environmentReady"); core.classList.add("success"); }
      }
    }
    $("#environment-jobs").innerHTML = jobs.slice(-4).reverse().map(job => `<section class="environment-job"><div class="row spread"><strong>${e(t(job.preset === "core" ? "environmentCore" : "environmentMathlib"))} · ${e(t("env_" + job.stage))}</strong>${["running", "queued"].includes(job.status) ? `<button type="button" data-cancel-env="${e(job.id)}">${e(t("cancel"))}</button>` : ""}</div>${job.progress !== null ? `<progress max="100" value="${Number(job.progress)}"></progress><small>${Number(job.progress)}%</small>` : ""}${job.totalBytes ? `<p>${(job.downloadedBytes / 1e6).toFixed(1)} / ${(job.totalBytes / 1e6).toFixed(1)} MB</p>` : ""}${job.error ? `<p class="danger">${e(job.error)}</p>` : ""}${job.result?.path ? `<p class="muted">${e(job.result.path)}</p>` : ""}<details><summary>${e(t("rawEvidence"))}</summary><pre>${e(job.log.join("\n"))}</pre></details></section>`).join("");
    d.querySelectorAll('[data-cancel-env]').forEach(b => b.onclick = () => api('/api/lean/environments/cancel', 'POST', {jobId:b.dataset.cancelEnv}).catch(fail));
  };
  renderJobs(info.jobs);
  d.querySelectorAll('[data-setup-env]').forEach(b => b.onclick = async () => {
    b.disabled = true;
    try { await api('/api/lean/environments/setup', 'POST', {preset:b.dataset.setupEnv}); await poll(); }
    catch (err) { fail(err); b.disabled = false; }
  });
  $("#register-environment").onclick = () => action("registerEnvironment").catch(fail);
  let previousReady = info.jobs.filter(j=>j.status === 'ready').length;
  async function poll() {
    clearTimeout(environmentTimer);
    if (!d.open || d.dataset.panel !== "environments") return;
    try {
      const jobs = (await api('/api/lean/environments/jobs')).jobs;
      if (!d.open || d.dataset.panel !== "environments") return;
      renderJobs(jobs);
      const ready = jobs.filter(j=>j.status === 'ready').length;
      if (ready !== previousReady) { state.envs = (await api('/api/lean/projects')).projects; previousReady = ready; }
    } catch (err) { fail(err); }
    if (d.open && d.dataset.panel === "environments") environmentTimer = setTimeout(poll, 1500);
  }
  environmentTimer = setTimeout(poll, 1500);
}

$("#trash").onclick = async () => {
  try {
    const rows = (await api("/api/trash")).proofs;
    dialog(
      "trash",
      `<p>${e(t("trashHint"))}</p>` +
        (rows
          .map(
            (p) =>
              `<div class="history-item row spread"><span>${e(p.title)}</span><button type="button" data-recover="${e(p.id)}">${e(t("restore"))}</button></div>`,
          )
          .join("") || `<p>${e(t("emptyTrash"))}</p>`),
    );
    $("#dialog")
      .querySelectorAll("[data-recover]")
      .forEach(
        (b) =>
          (b.onclick = async () => {
            try {
              await api(
                "/api/trash/" +
                  encodeURIComponent(b.dataset.recover) +
                  "/restore",
                "POST",
                {},
              );
              $("#dialog").close();
              await list();
              toast(t("restored"));
            } catch (err) {
              fail(err);
            }
          }),
      );
  } catch (err) {
    fail(err);
  }
};
window.addEventListener("beforeunload", (event) => {
  if (state.dirty) {
    event.preventDefault();
    event.returnValue = "";
  }
});
let refreshTimer;
function scheduleRefresh() {
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(() => refresh().catch(fail), 350);
}
function decorateIcons() {
  const items = {
    "#new-chat": ["plus", "newChat", false],
    "#new-project": ["folder", "newProject", true],
    "#settings": ["settings", "settings", false],
    "#trash": ["trash", "trash", false],
    "#environments": ["code", "manageEnvironments", false],
    "#send": ["send", "send", true],
    "#pause": ["pause", "pause", true],
    "#toggle-sidebar": ["sidebar", "toggleSidebar", true],
  };
  for (const [selector, [name, label, only]] of Object.entries(items)) {
    const el = $(selector);
    el.innerHTML = icon(name) + (only ? "" : `<span>${e(t(label))}</span>`);
    el.title = t(label);
    el.setAttribute("aria-label", t(label));
    el.classList.toggle("icon-only", only);
  }
  $("#actions summary").innerHTML = icon("more");
  for (const el of document.querySelectorAll("[data-view]"))
    el.innerHTML =
      icon(
        { conversation: "chat", document: "research", lean: "code" }[
          el.dataset.view
        ],
      ) + `<span>${e(t(el.dataset.view))}</span>`;
  renderModelChoices();
}
function renderModelChoices() {
  const selected = state.settings.provider === "api" ? state.settings.apiModel : state.settings.model || "";
  $("#model-select").innerHTML =
    `<option value="">${e(t("defaultModel"))}</option>` +
    state.models
      .map(
        (m) =>
          `<option value="${e(m.model)}" ${m.model === selected ? "selected" : ""}>${e(m.displayName)}</option>`,
      )
      .join("");
  if (selected && !state.models.some((m) => m.model === selected))
    $("#model-select").insertAdjacentHTML(
      "beforeend",
      `<option value="${e(selected)}" selected>${e(selected)}</option>`,
    );
  const model =
    state.models.find((m) => m.model === selected) ||
    state.models.find((m) => m.isDefault);
  $("#effort-select").innerHTML =
    `<option value="">${e(t("defaultEffort"))}</option>` +
    (model?.supportedReasoningEfforts || [])
      .map(
        (r) =>
          `<option value="${e(r.reasoningEffort)}" ${state.settings.effort === r.reasoningEffort ? "selected" : ""}>${e(t(r.reasoningEffort))}</option>`,
      )
      .join("");
  $("#model-select").setAttribute("aria-label", t("model"));
  $("#effort-select").setAttribute("aria-label", t("effort"));
}
async function loadModels() {
  if (state.settings.provider === "api") {
    state.models = [{model: state.settings.apiModel, displayName: state.settings.apiModel}];
    $("#model-retry").hidden = true;
    renderModelChoices();
    $("#model-select").disabled = true;
    $("#effort-select").hidden = true;
    return;
  }
  $("#model-select").disabled = false;
  $("#effort-select").hidden = false;
  try {
    state.models = (await api("/api/codex/models")).models;
    $("#model-retry").hidden = true;
    renderModelChoices();
  } catch (err) {
    $("#model-retry").hidden = false;
    $("#model-retry").title = t("modelError");
  }
}
$("#model-retry").onclick = loadModels;
$("#model-select").onchange = async (event) => {
  try {
    state.settings = (
      await api("/api/settings", "PUT", {
        model: event.target.value,
        effort: "",
      })
    ).settings;
    renderModelChoices();
  } catch (err) {
    fail(err);
  }
};
$("#effort-select").onchange = async (event) => {
  try {
    state.settings = (
      await api("/api/settings", "PUT", { effort: event.target.value })
    ).settings;
  } catch (err) {
    fail(err);
  }
};
async function init() {
  translate();
  $("#content").innerHTML = `<div class="page muted">${e(t("loading"))}</div>`;
  const [settings, envs, status] = await Promise.all([
    api("/api/settings"),
    api("/api/lean/projects"),
    api("/api/codex/status"),
  ]);
  state.settings = settings.settings;
  state.envs = envs.projects;
  state.runningProof = status.busy ? status.proofId : null;
  setLanguage(state.settings.language);
  await list();
  const active = localStorage.getItem("proveit.active");
  if (active && state.proofs.some((p) => p.id === active))
    await openProof(active);
  else render();
  api("/api/lean/environments").then(r => { $("#environment-notice").hidden = r.environments.leanReady; }).catch(fail);
  const connection = await api("/api/connection");
  $("#connection-status").onclick = () => openSettings();
  if (state.settings.provider === "api" && connection.keyConfigured && state.settings.apiModel) {
    await loadModels();
    state.connectionLabel = "customApi"; $("#connection-status").textContent = t(state.connectionLabel);
  } else {
    try { await api("/api/connection/test", "POST", {}); await loadModels(); state.connectionLabel = "connectionReady"; $("#connection-status").textContent = t(state.connectionLabel); }
    catch { openSettings(true); }
  }
  const events = new EventSource("/api/events");
  events.onmessage = (event) => {
    const { method, params: p = {} } = JSON.parse(event.data);
    if (method === "environment/progress") {
      if (["running", "queued"].includes(p.job?.status)) $("#run-state").textContent = t("env_" + p.job.stage);
      if (p.job?.status === "ready") { $("#environment-notice").hidden = true; }
      if (p.job?.status === "ready") api("/api/lean/projects").then(r => { state.envs = r.projects; scheduleRefresh(); }).catch(fail);
      return;
    }
    if (method === "turn/started") state.runningProof = p.proofId;
    if (
      ["research/idle", "bridge/closed"].includes(method) &&
      state.runningProof === p.proofId
    )
      state.runningProof = null;
    if (p.proofId && p.proofId !== state.proof?.id) {
      chrome();
      return;
    }
    if (method === "research/timeline") {
      const index = state.timeline.findIndex(
        (item) => item.event_key === p.entry.event_key,
      );
      if (index < 0) state.timeline.push(p.entry);
      else state.timeline[index] = p.entry;
      const target = $("#timeline");
      if (target) {
        const follow =
          $("#content").scrollHeight -
            $("#content").scrollTop -
            $("#content").clientHeight <
          100;
        const current = [...target.children].find(
          (el) => el.dataset.event === p.entry.event_key,
        );
        const holder = document.createElement("div");
        holder.innerHTML = timelineEntry(p.entry, md);
        if (current) {
          const open = current.open;
          const replacement = holder.firstElementChild;
          if (open) replacement.open = true;
          current.replaceWith(replacement);
        } else target.append(holder.firstElementChild);
        if (follow) $("#content").scrollTop = $("#content").scrollHeight;
      }
    } else if (method === "turn/started") {
      state.runningProof = p.proofId;
      chrome();
      if ($("#thinking")) $("#thinking").innerHTML = thinking();
    } else if (
      [
        "turn/completed",
        "research/idle",
        "bridge/closed",
        "bridge/error",
      ].includes(method)
    ) {
      if (method !== "turn/completed") state.runningProof = null;
      if (method === "bridge/error")
        toast(errorText(p.message || p.error || t("failed")));
      scheduleRefresh();
      chrome();
      if ($("#thinking") && !state.busy) $("#thinking").innerHTML = "";
    } else if (
      [
        "proof/artifactUpdated",
        "research/updated",
        "proof/checkResult",
      ].includes(method)
    )
      scheduleRefresh();
  };
  events.onerror = () => {
    $("#run-state").textContent = t("reconnecting");
  };
  events.onopen = () => {
    api("/api/codex/status")
      .then((status) => {
        state.runningProof = status.busy ? status.proofId : null;
        chrome();
        scheduleRefresh();
      })
      .catch(fail);
  };
}
init().catch(fail);
