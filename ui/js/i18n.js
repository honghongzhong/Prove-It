/** All application-owned copy lives here; research content is never auto-translated. */
const copy = {
  environmentMissingHint: ["Lean 环境尚未就绪。检查证明时可自动安装，也可以现在一键配置。", "Lean is not ready. Missing environments can be installed automatically when checking, or configured now."],
  manageEnvironments: ["Lean 环境", "Lean environments"],
  environmentManager: ["环境管理", "Environment manager"],
  environmentIntro: ["一键配置 Lean 核心或 Mathlib。优先复用匹配版本的现有安装，缺失时下载；安装后会实际运行 Lean 检查。", "Set up Lean core or Mathlib in one click. Matching existing installations are reused; missing components are downloaded and checked with real Lean."],
  environmentCore: ["Lean 核心", "Lean core"],
  environmentMathlib: ["Mathlib 常用数学环境", "Mathlib mathematics environment"],
  environmentCoreHint: ["Lean、Lake、标准库。新安装下载约 850 MB，至少需要 4 GB 空间。", "Lean, Lake and the standard library. A fresh download is about 850 MB; at least 4 GB free space is required."],
  environmentMathlibHint: ["Mathlib、Batteries、Aesop、Qq 及匹配依赖和编译缓存。至少需要 8 GB 空间。", "Mathlib, Batteries, Aesop, Qq, matching dependencies and compiled caches. At least 8 GB free space is required."],
  setupEnvironment: ["安装 / 检查", "Set up / Check"],
  environmentReady: ["已就绪", "Ready"],
  environmentMissing: ["未配置", "Not configured"],
  autoSetupLean: ["自动配置缺失的常用 Lean 环境（允许下载）", "Automatically set up missing common Lean environments (allow downloads)"],
  environmentProxy: ["下载代理（可选，例如 http://127.0.0.1:10808）", "Download proxy (optional, e.g. http://127.0.0.1:10808)"],
  environmentJobHint: ["进度百分比表示当前阶段；可取消，重试会复用已下载内容。", "Percentages describe the current stage. Cancel is available; retries reuse downloaded content."],
  environmentOpen: ["查看安装进度", "View setup progress"],
  env_queued: ["等待安装", "Queued"],
  env_checking: ["检查现有环境", "Checking existing environment"],
  env_downloading: ["下载", "Downloading"],
  env_checksum: ["校验文件", "Checking archive checksum"],
  env_extracting: ["解压", "Extracting"],
  env_cloning: ["下载 Mathlib 源码", "Downloading Mathlib sources"],
  env_dependencies: ["配置依赖及编译缓存", "Fetching dependencies and cache"],
  env_verifying: ["运行 Lean 检查", "Running Lean checks"],
  env_ready: ["安装完成，检查通过", "Setup complete; checks passed"],
  env_failed: ["安装失败，可重试", "Setup failed; retry available"],
  env_cancelled: ["安装已取消，可继续", "Setup cancelled; can resume"],
  env_interrupted: ["安装被中断，可继续", "Setup interrupted; can resume"],

  connectionSetup: ["连接模型", "Connect a model"],
  connectionHint: ["选择 Codex 或填写自己的 API。未连接时仍可查看和编辑本地研究。", "Choose Codex or configure your own API. Local research remains available while disconnected."],
  provider: ["模型来源", "Model provider"],
  customApi: ["自定义 API（OpenAI 兼容）", "Custom API (OpenAI compatible)"],
  baseUrl: ["Base URL（通常以 /v1 结尾）", "Base URL (usually ends in /v1)"],
  apiModel: ["Model Name", "Model name"],
  apiKey: ["API Key（留空保留已有密钥）", "API key (leave blank to keep saved key)"],
  clearKey: ["删除已保存密钥", "Remove saved key"],
  codexPath: ["Codex 可执行文件路径（可选）", "Codex executable path (optional)"],
  codexGuide: ["在 PowerShell 安装：npm install -g @openai/codex；然后运行 codex login。若已安装但无法找到，请填入 codex.exe 的完整路径，然后保存并测试连接。ProveIt 会自行建立工作会话，无需在 Codex 中另建项目。", "In PowerShell: npm install -g @openai/codex, then run codex login. If detection fails, enter the full codex.exe path, save and test. ProveIt creates its own working session; a separate Codex project is unnecessary."],
  testConnection: ["保存并测试连接", "Save and test connection"],
  connectionReady: ["模型连接已就绪", "Model connection ready"],
  connectionOffline: ["模型未连接 · 点击设置", "Model disconnected · Open settings"],
  generalSettings: ["外观与编辑", "Appearance and editing"],
  modelSettings: ["模型连接", "Model connection"],
  deleteProject: ["移除项目分组", "Remove project grouping"],
  deleteProjectHint: ["研究对话会保留并移到未分组列表。", "Research conversations will be retained and moved to Ungrouped."],

  toolCompleted: ["已完成", "Completed"],
  model: ["模型", "Model"],
  defaultModel: ["Codex 默认模型", "Codex default"],
  effort: ["思考深度", "Reasoning effort"],
  defaultEffort: ["默认深度", "Default effort"],
  low: ["较低", "Low"],
  medium: ["中等", "Medium"],
  high: ["高", "High"],
  xhigh: ["很高", "Extra high"],
  max: ["最大", "Maximum"],
  ultra: ["极高", "Ultra"],
  minimal: ["最少", "Minimal"],
  interrupted: ["已中断", "Interrupted"],
  thinking: ["模型正在工作", "Model is working"],
  loadingModels: ["正在读取模型…", "Loading models…"],
  modelError: ["无法读取模型列表，点击重试", "Cannot load models. Retry"],
  sessionRecovered: [
    "原会话无法恢复，已用保存的研究和对话恢复工作会话。",
    "The original session could not be resumed. A new working session was restored from saved research and conversation.",
  ],
  exportMarkdown: ["导出 Markdown", "Export Markdown"],

  tagline: ["数学研究工作台", "A workspace for mathematical research"],
  newChat: ["新建研究", "New research"],
  projects: ["项目", "Projects"],
  newProject: ["新建项目", "New project"],
  conversations: ["未分组的研究", "Ungrouped research"],
  search: ["搜索项目与研究…", "Search projects and research…"],
  emptySearch: ["没有匹配的研究", "No matching research"],
  emptyProject: ["这个项目还没有研究", "No research in this project yet"],
  renameProject: ["重命名项目", "Rename project"],
  projectName: ["项目名称", "Project name"],
  namePlaceholder: ["例如：数论中的问题", "e.g. Questions in number theory"],
  conversation: ["对话", "Conversation"],
  document: ["研究", "Research"],
  lean: ["Lean", "Lean"],
  renameChat: ["重命名研究", "Rename research"],
  moveChat: ["移动到项目", "Move to project"],
  ungrouped: ["未分组", "Ungrouped"],
  title: ["研究标题", "Research title"],
  more: ["研究操作", "Research actions"],
  trash: ["回收站", "Trash"],
  trashChat: ["移至回收站", "Move to trash"],
  restore: ["恢复", "Restore"],
  emptyTrash: ["回收站为空", "Trash is empty"],
  trashHint: [
    "研究、代码与记录会保留，可随时恢复。",
    "Your research, source and records are retained and can be restored.",
  ],
  move: ["移动", "Move"],
  cancel: ["取消", "Cancel"],
  save: ["保存", "Save"],
  close: ["关闭", "Close"],
  settings: ["设置", "Settings"],
  language: ["界面语言", "Language"],
  theme: ["外观", "Appearance"],
  light: ["浅色", "Light"],
  dark: ["深色", "Dark"],
  autoSave: ["自动保存 Lean 代码", "Autosave Lean source"],
  autoVerify: ["保存代码后自动检查", "Check after saving source"],
  settingsHint: [
    "界面语言用于新的 AI 回复；已有研究内容保持原文。",
    "The language applies to new AI responses. Existing research keeps its original language.",
  ],
  saved: ["已保存", "Saved"],
  saving: ["保存中…", "Saving…"],
  unsaved: ["有未保存的修改", "Unsaved changes"],
  saveFailed: ["保存失败", "Save failed"],
  requestFailed: [
    "操作未完成，请查看详情。",
    "The action could not be completed. See details.",
  ],
  loading: ["正在载入…", "Loading…"],
  local: ["本地工作区", "Local workspace"],
  heroTitle: ["从一个数学问题开始", "Begin with a mathematical question"],
  heroBody: [
    "明确目标，探索证明，让 Lean 检查每一次实质进展。",
    "Clarify the goal, explore a proof, and let Lean check your progress.",
  ],
  composerPlaceholder: [
    "描述你的问题，或给出下一步研究方向…",
    "Describe your question, or suggest a direction…",
  ],
  composerHint: [
    "Enter 发送 · Shift + Enter 换行",
    "Enter to send · Shift + Enter for a new line",
  ],
  send: ["发送", "Send"],
  pause: ["暂停研究", "Pause research"],
  resume: ["继续研究", "Continue research"],
  discuss: ["回到对话", "Back to conversation"],
  you: ["你", "You"],
  assistant: ["Codex", "Codex"],
  noMessages: ["从这里继续你的研究", "Continue your research here"],
  noMessagesHint: [
    "提出证明方法、补充假设，或请 Codex 根据当前研究继续推进。",
    "Suggest an approach, clarify assumptions, or ask Codex to continue from your research.",
  ],
  example1: [
    "证明素数有无穷多个",
    "Prove that there are infinitely many primes",
  ],
  example2: ["探索一个不等式的证明", "Explore a proof of an inequality"],
  boundary: [
    "Lean 验证形式命题；目标含义、假设与研究价值由你审阅。",
    "Lean checks the formal proposition. You review its meaning, assumptions and significance.",
  ],
  goal: ["研究目标", "Research goal"],
  goalHint: [
    "先明确要证明什么，以及证明成立的前提。",
    "Make the intended statement and its assumptions explicit.",
  ],
  edit: ["编辑", "Edit"],
  goalEmpty: ["还没有登记目标", "No goal registered yet"],
  goalEmptyHint: [
    "与 Codex 讨论后，精确目标会显示在这里。也可以手动添加。",
    "Discuss the problem with Codex to define a precise goal, or add one yourself.",
  ],
  assumptions: ["约定与假设", "Scope and assumptions"],
  noAssumptions: ["未额外说明假设", "No additional assumptions specified"],
  formalDetails: ["查看形式化目标", "View formal target"],
  naturalGoal: ["自然语言目标", "Goal in natural language"],
  targetName: ["Lean 定理全名", "Fully qualified Lean theorem name"],
  formalType: ["完整 Lean 命题类型", "Complete Lean proposition type"],
  formalHint: [
    "包括全部量词与假设，例如 ∀ n : Nat, n + 0 = n。通常由 Codex 填写。",
    "Include every quantifier and assumption, e.g. ∀ n : Nat, n + 0 = n. Codex normally fills this in.",
  ],
  review: ["确认含义与假设", "Review meaning and assumptions"],
  reviewed: ["含义与假设已审阅", "Meaning and assumptions reviewed"],
  unreview: ["撤销审阅", "Undo review"],
  reviewHint: [
    "只确认当前目标的含义与假设，不代表证明已经完成。",
    "This reviews the current statement and assumptions, not whether the proof is complete.",
  ],
  steps: ["证明路线", "Proof outline"],
  stepsHint: [
    "把论证拆为可以逐步推进的步骤。",
    "Break the argument into steps you can work on.",
  ],
  addStep: ["添加步骤", "Add step"],
  stepTitle: ["步骤标题", "Step title"],
  stepContent: [
    "论证、证据与未解部分",
    "Argument, evidence and open questions",
  ],
  stepStatus: ["进展", "Progress"],
  dependsOn: ["依赖步骤", "Depends on"],
  dependencies: ["依赖", "Depends on"],
  dependencyHint: [
    "按住 Ctrl / ⌘ 选择多个步骤。",
    "Hold Ctrl / ⌘ to select multiple steps.",
  ],
  declaration: ["对应 Lean 声明（可选）", "Lean declaration (optional)"],
  planned: ["待探索", "Planned"],
  working: ["推进中", "In progress"],
  candidate: ["候选论证", "Candidate argument"],
  blocked: ["需要方向", "Needs direction"],
  stepsEmpty: ["还没有证明步骤", "No proof steps yet"],
  stepsEmptyHint: [
    "让 Codex 提出路线，或记录你的第一个想法。",
    "Ask Codex for an outline, or record your first idea.",
  ],
  proof: ["自然语言证明", "Written proof"],
  proofHint: [
    "完整论证统一保存在这里，可随时阅读和修订。",
    "Keep the complete argument in a readable, editable document.",
  ],
  proofEmpty: ["证明尚未整理", "No written proof yet"],
  proofEmptyHint: [
    "Codex 保存的自然语言证明会出现在这里。",
    "The written proof saved by Codex will appear here.",
  ],
  markdown: ["正文（支持 Markdown）", "Content (Markdown supported)"],
  source: ["证明源码", "Proof source"],
  saveSource: ["保存源码", "Save source"],
  check: ["运行 Lean", "Run Lean"],
  checking: ["正在运行 Lean…", "Running Lean…"],
  sourceHint: [
    "源码与自然语言证明分别保存。更改代码后，需要重新验证。",
    "Source and written proof are saved separately. Recheck after changing the code.",
  ],
  environment: ["Lean 环境", "Lean environment"],
  core: ["Lean 核心环境", "Lean core"],
  addEnvironment: ["添加 Lean 环境", "Add Lean environment"],
  envName: ["环境名称", "Environment name"],
  envPath: ["Lake 项目目录", "Lake project directory"],
  envHint: [
    "选择包含 lakefile.toml 或 lakefile.lean 的本地目录。",
    "Use a local directory containing lakefile.toml or lakefile.lean.",
  ],
  evidence: ["验证结果", "Verification"],
  unchecked: ["尚未验证", "Not checked"],
  verified: ["形式目标已验证", "Formal target verified"],
  rejected: ["检查未通过", "Check failed"],
  stale: ["结果已过期", "Result out of date"],
  unavailable: ["工具不可用", "Tool unavailable"],
  timeout: ["检查超时", "Check timed out"],
  formalization_checked: [
    "仅源码编译通过",
    "Source compiled; target not verified",
  ],
  evidenceEmpty: [
    "运行 Lean 后，这里会显示实际结果。",
    "Run Lean to see the actual verification result.",
  ],
  evidencePass: [
    "Lean 已接受登记的目标类型和证明。自然语言对应关系仍需审阅。",
    "Lean accepted the registered target type and proof. The natural-language interpretation still needs review.",
  ],
  staleHint: [
    "源码、目标或环境已变化，请重新检查。",
    "The source, goal or environment changed. Run a new check.",
  ],
  diagnostics: ["诊断", "Diagnostics"],
  rawEvidence: ["完整验证记录", "Full verification record"],
  axioms: ["公理依赖", "Axiom dependencies"],
  none: ["无", "None"],
  exportSource: ["导出 Lean 文件", "Export Lean file"],
  exportResearch: ["导出研究记录", "Export research record"],
  history: ["版本历史", "Version history"],
  sourceHistory: ["源码版本", "Source versions"],
  outlineHistory: ["目标与步骤版本", "Goal and outline versions"],
  noHistory: ["尚无历史版本", "No earlier versions yet"],
  restoreVersion: ["恢复此版本", "Restore version"],
  restoreHint: [
    "当前版本会保留在历史中。恢复目标与步骤后，需要重新审阅。",
    "The current version stays in history. Restored goals and steps need a fresh review.",
  ],
  projectCreated: ["项目已创建", "Project created"],
  projectRenamed: ["项目已重命名", "Project renamed"],
  moved: ["研究已移动", "Research moved"],
  renamed: ["研究已重命名", "Research renamed"],
  restored: ["已恢复", "Restored"],
  paused: ["已暂停", "Paused"],
  idle: ["等待研究方向", "Ready for a direction"],
  running: ["Codex 正在研究", "Codex is working"],
  completed: ["本轮已完成", "Turn complete"],
  failed: ["研究中断", "Research interrupted"],
  connected: ["Codex 已连接", "Codex connected"],
  disconnected: ["Codex 未连接", "Codex disconnected"],
  reconnecting: ["正在重连…", "Reconnecting…"],
  toolRead: ["读取研究状态", "Reading research"],
  toolGoal: ["更新目标与步骤", "Updating the goal and outline"],
  toolSource: ["保存 Lean 候选", "Saving Lean source"],
  toolProof: ["保存自然语言证明", "Saving the written proof"],
  toolLean: ["运行 Lean 检查", "Running Lean"],
  toolCandidate: ["检查辅助候选", "Checking a supporting candidate"],
  toolBlocked: ["记录研究障碍", "Recording an obstacle"],
  toolGeneric: ["执行研究工具", "Running a research tool"],
  activity: ["工具活动", "Tool activity"],
  activityEmpty: ["工具活动会显示在这里", "Tool activity will appear here"],
  pendingPause: [
    "已请求暂停；当前 Lean 检查会在返回或超时后结束。",
    "Pause requested. An active Lean check will finish or time out.",
  ],
  queued: [
    "新方向已排队，当前轮次结束后继续。",
    "Your direction is queued and will continue after this turn.",
  ],
  resumePrompt: [
    "请读取当前目标、步骤和验证证据，沿现有研究方向继续推进。",
    "Read the current goal, steps and verification evidence, and continue the research.",
  ],
  sourceConflict: [
    "源码已在其他操作中更新。请保留本地编辑，重新打开后合并。",
    "The saved source changed elsewhere. Keep your edits and reopen to merge them.",
  ],
  revisionConflict: [
    "研究已更新。请关闭表单，重新读取后再编辑。",
    "The research was updated. Close this form and reopen it before editing.",
  ],
  discardChanges: [
    "有未保存的 Lean 编辑。放弃这些修改并继续？",
    "There are unsaved Lean edits. Discard them and continue?",
  ],
  noSource: ["请先保存一份 Lean 候选源码。", "Save a Lean candidate first."],
  chooseResearch: [
    "请先打开或创建一个研究。",
    "Open or create a research conversation first.",
  ],
  projectMissing: ["找不到这个项目。", "Project not found."],
  conversationMissing: ["找不到这个研究。", "Conversation not found."],
  nameRequired: ["名称不能为空。", "A name is required."],
  pauseBeforeDelete: [
    "请先暂停研究，再移至回收站。",
    "Pause the research before moving it to trash.",
  ],
  toggleSidebar: ["切换项目栏", "Toggle sidebar"],
  closeSidebar: ["关闭项目栏", "Close sidebar"],
  chooseProject: ["所属项目", "Project"],
  add: ["添加", "Add"],
  savedChanges: ["修改已保存", "Changes saved"],
};
let language = "en";
export function setLanguage(value) {
  language = value === "zh" ? "zh" : "en";
  document.documentElement.lang = language === "en" ? "en" : "zh-CN";
}
export function getLanguage() {
  return language;
}
export function t(key) {
  if (!copy[key]) throw new Error(`Missing translation: ${key}`);
  return copy[key][language === "en" ? 1 : 0];
}
export function translate(root = document) {
  root.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  root.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  root.querySelectorAll("[data-i18n-label]").forEach((el) => {
    el.setAttribute("aria-label", t(el.dataset.i18nLabel));
    el.title = t(el.dataset.i18nLabel);
  });
}
export function date(value) {
  return value
    ? new Intl.DateTimeFormat(language === "en" ? "en-GB" : "zh-CN", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(value))
    : "";
}
export function errorText(message = "") {
  if (/源码已|source.*changed/i.test(message)) return t("sourceConflict");
  if (/研究状态已|自然语言证明已/.test(message)) return t("revisionConflict");
  if (/Project not found/.test(message)) return t("projectMissing");
  if (/找不到这个证明|Conversation not found/.test(message))
    return t("conversationMissing");
  if (/不能为空|required/i.test(message)) return t("nameRequired");
  if (/请先暂停/.test(message)) return t("pauseBeforeDelete");
  return language === "zh" || !/[\u4e00-\u9fff]/.test(message)
    ? message
    : t("requestFailed");
}
