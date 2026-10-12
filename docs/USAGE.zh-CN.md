# 使用手册

[English](USAGE.md) · 简体中文

## 第一次运行

1. 新建项目，例如“基础代数”，再新建研究。
2. 在对话中输入：“请形式化并证明，对任意自然数 n，有 n + 0 = n。使用 Lean 核心环境。”选择可用模型和思考深度后发送。
3. 在“研究”检查 AI 提出的量词、假设、自然语言目标与形式目标。确认含义不代表确认已经证明。
4. 在“Lean”查看保存代码与实际检查证据；检查目标应是完整命题，而不是辅助引理。
5. 补充“请解释为什么可以使用 rfl”或提出自己的方向。工具操作与正文按照发生顺序显示。

也可手动登记以下测试目标，不依赖模型生成代码：

- 目标名：`ProveIt.nat_add_zero`
- 完整类型：`∀ n : Nat, n + 0 = n`

```lean
namespace ProveIt
theorem nat_add_zero : ∀ n : Nat, n + 0 = n := by
  intro n
  rfl
end ProveIt
```

保存后在 Lean 页执行检查。只有本机真实返回成功才算通过。

## 研究者与 AI 协作

新方向会中断当前轮次并排队继续。“暂停”停止自动续轮；正在运行的 Lean 检查可能要等返回或超时。每次请求默认最多 8 轮，没有实质进展或缺少信息时停止。AI 可以提出或修订目标、步骤和证明，但不能替你确认人工审阅。

源码与研究状态使用版本冲突检查，避免模型覆盖你刚保存的修改。新工作区默认英文，可在 Settings 中选择中文，已有用户的语言偏好会保留。已有对话保留原语言；界面语言影响新回复，不自动翻译历史研究。

## 导出与恢复

顶部研究菜单可以导出 Markdown、JSON 和 Lean。Markdown 适合阅读、分享，包含目标、论证、代码、检查摘要与对话/工具记录；JSON 包含更多修订历史。历史菜单恢复旧版本时会产生新修订。

回收站可以恢复删除的研究。目前没有“导入导出 JSON 以恢复整个工作区”的功能。完整备份请退出应用后复制整个 workspace 目录，包含 proofs 和 .proveit；恢复时同样退出应用再放回该目录。

默认桌面数据目录：`%APPDATA%/ProveIt/workspace`。源码版默认数据目录为项目根，可用 PROVEIT_DATA_DIR 指定。

从旧源码版迁移：退出两边服务，把旧目录里的 `proofs/` 和 `.proveit/workspace.sqlite3`（以及存在的 SQLite -wal/-shm 文件）复制到桌面 workspace 下相同位置。先备份桌面 workspace，不要直接覆盖已有研究；Lake 环境路径需在新机器重新登记。

卸载默认保留用户数据。ZIP 版仍使用用户数据目录，不把研究放在 EXE 旁边。发布研究记录前自行检查其中的私密内容。

## 配置

| 变量 | 用途 | 默认 |
| --- | --- | --- |
| PROVEIT_DATA_DIR | 源码版工作区路径 | 项目目录 |
| PROVEIT_DESKTOP_DATA_DIR | 桌面用户数据目录覆盖 | Electron userData |
| PROVEIT_PORT | 源码版端口 | 8765 |
| LEAN_EXE / LAKE_EXE / CODEX_EXE | 可执行文件路径 | PATH |
| PROVEIT_MAX_TURNS | 自动轮数上限 | 8 |
| PROVEIT_TURN_TIMEOUT | 单个 Codex 轮次秒数 | 1800 |
| PROVEIT_LEAN_TIMEOUT | 单次 Lean 检查秒数 | 120 |

桌面端随机分配回环端口，仅应用持有后端进程。不要从安装目录手动启动后端。源代码模式可运行 `python app.py`。

## 研究中的环境配置

侧栏环境管理提供 Lean 核心和 Mathlib 预设。模型可调用 `proveit_get_environments` 和 `proveit_setup_environment`；实际验证前也可自动配置缺失的常用环境。在核心环境检查含 `import Mathlib` 的代码时，安装后自动选择管理的 Mathlib 项目。安装成功只表示代表性示例通过，不会把研究目标标记为已验证；目标仍需独立检查保存的源码、完整类型和公理依赖。建议按需导入具体 Mathlib 模块。

安装期间可以暂停研究。共享安装可能继续服务其它工作，可在环境管理中另行取消；重试会复用下载文件和管理的缓存。若关闭设置中的自动配置选项，则需主动通过环境管理安装。
