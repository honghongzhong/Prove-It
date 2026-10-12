# ProveIt

**面向数学研究者的 AI 辅助工作台 · An AI-assisted mathematical research workspace**

[下载安装包 / Download](https://github.com/honghongzhong/Prove-It/releases/latest) · [安装说明](docs/INSTALL.zh-CN.md) · [使用手册](docs/USAGE.zh-CN.md) · [English](README.md) · [构建与发布](docs/DEVELOPMENT.zh-CN.md)

ProveIt 连接 **Codex** 的研究与编码能力和 **Lean 4** 的形式化检查。研究者提出问题、澄清假设、指明方向；AI 保存目标、分解步骤、修订自然语言论证与 Lean 代码，并根据真实诊断继续迭代。

![ProveIt desktop workspace](docs/assets/workspace.png)

## 下载与启动

Windows x64 用户从 [Releases](https://github.com/honghongzhong/Prove-It/releases) 下载 `ProveIt-*-windows-x64-setup.exe`。也提供 ZIP 免安装版：完整解压后运行 `ProveIt.exe`，不要单独移动 EXE。

安装包内置 Electron 与 Python 后端，**无需另装 Python**。需要自行安装 **Lean 4 / Elan** 和 **已登录的 Codex CLI**。Mathlib 是可选的外部 Lake 项目。安装与排错见 [INSTALL.md](docs/INSTALL.zh-CN.md)。当前发布 Windows x64；未发布 macOS / Linux 桌面安装包。

本版未使用代码签名证书，Windows 可能显示未知发布者提示。请核对本仓库发布页及 SHA-256；不要关闭系统安全防护。ProveIt 不是 OpenAI 或 Lean 的官方产品。

## 工作区

- **项目侧栏**：创建、重命名、搜索和归类研究，回收站可恢复删除的研究。
- **对话**：选择模型及思考深度，实时查看回复与穿插的工具调用；随时补充方向、暂停或继续。
- **研究**：自然语言目标、假设、完整形式化目标、证明路线和正文；独立人工审阅状态。
- **Lean**：源码、环境、真实检查、诊断及与当前产物绑定的证据。
- **导出**：Lean 源码、排版 Markdown、包含修订历史的 JSON。
- **显示**：新安装默认英文，可切换中文；黑白双主题、本地字体与 KaTeX 公式渲染。

## 从源码运行

需要 Python 3.11+，后端只使用标准库：

```powershell
git clone https://github.com/honghongzhong/Prove-It.git
cd Prove-It
lean --version
codex --version
codex login
python app.py
```

打开 http://127.0.0.1:8765 。桌面开发和安装包构建见 [开发说明](docs/DEVELOPMENT.zh-CN.md)。

## 验证边界

只有实际运行 Lean、完整登记目标类型成立、公理依赖通过审计，才标记形式目标已验证。局部引理、有限实例和候选编译成功不会替代完整目标。拒绝 `sorryAx` 和额外公理；接受的常用基础公理为 `propext`、`Classical.choice`、`Quot.sound`。修改源码、目标或环境会使旧证据过期。

**Lean 验证编码后的命题，不验证自然语言翻译的忠实性、假设的合理性、研究的新颖性或意义。** 这些由研究者审阅。ProveIt 不保证 AI 能解决提出的数学问题。

## 数据与隐私

桌面版研究保存在 `%APPDATA%/ProveIt/workspace`，与安装目录分开；源码版默认保存在仓库本地 `proofs/` 与 `.proveit/`。详细备份与迁移见使用手册。

仓库和安装包不包含作者的研究、聊天、账号、数据库、日志、Lean/Mathlib 工作目录或 Codex 凭据。`.gitignore`、安装包资源白名单和发布检查共同限制发布内容。

Codex 会接收你主动提交的研究及相关上下文，并按你自己的账号、模型提供方和配置处理。ProveIt 本身不增加遥测，也不收集登录密码。Lean 元编程、Lake 项目及 Codex 工具可能执行本机代码：仅用于可信本地研究环境，不是执行不可信代码的安全沙箱；不要公开转发后端端口。

## 贡献与许可证

欢迎通过 [Issues](https://github.com/honghongzhong/Prove-It/issues) 提交复现步骤，上传前删除研究内容、令牌和本地路径。贡献流程见 [CONTRIBUTING.md](CONTRIBUTING.zh-CN.md)。

沿用仓库原有 [MIT License](LICENSE)。依赖许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.zh-CN.md)。

文档与发行包遵循[语言规范](docs/LANGUAGE_POLICY.zh-CN.md)。

### 使用自己的 API 模型

打开“设置 → 模型连接 → 自定义 API”，输入 API Key、OpenAI 兼容的 Base URL（按服务商要求包含 `/v1`）和准确的 Model Name。“保存并测试连接”会发起一个小型推理请求，可能产生服务商费用。此模式无需安装 Codex；服务端需支持 Chat Completions 和研究工具所用的函数调用。远程地址要求 HTTPS，本地地址允许 HTTP。

Windows 使用当前用户的 DPAPI 加密密钥，保存在本地数据目录，不通过设置接口或研究导出返回。密钥框留空保留原密钥，勾选“删除已保存密钥”可清除。API 研究限制工具迭代次数；暂停后，正在进行的网络请求返回时不会继续写入产物（网络超时为 60 秒）。

没有就绪模型连接时，启动会打开连接指南。ProveIt 探测 Codex 安装位置、检查账户状态并自行创建工作会话，也允许在设置中指定可执行文件路径。项目分组支持重命名和移除，移除不会删除研究对话。

### 自动配置 Lean 环境

点击侧栏 **Lean 环境**，可安装或检查 Lean 核心与 Mathlib。软件优先复用版本匹配、能实际运行的安装；否则将官方 Windows x64 Lean/Lake 下载到软件数据目录。Mathlib 会同步获取固定版本的依赖和编译缓存；缺少 Git 时会自动下载便携 Git。Lean 与 Mathlib 配套固定为 v4.34.1。Lean 和 Git 压缩包在解压前核对固定的 SHA-256，环境必须经过实际 Lean 检查才能显示就绪。

默认启用 **自动配置缺失的常用 Lean 环境**。在核心环境检查包含 `import Mathlib` 的代码时，会自动准备并选择 Mathlib 项目。Codex 与自定义 API 模型均可检查环境，并调用限定为 `core` 或 `mathlib` 的配置工具；模型不能传入任意安装地址、命令或路径。关闭此设置后，需通过环境管理界面主动安装。已有用户项目和系统默认工具链保留。

安装任务展示阶段进度和日志，支持取消、重试；服务器支持分段请求时可继续未完成的压缩包下载。软件重启后，未完成任务标记为中断，可重试继续。暂停研究会停止该研究等待和写入产物；共享安装可能继续，可在环境管理中另行取消。设置中可填写下载代理。全新 Lean 下载约 850 MB，至少预留 4 GB；Mathlib 至少预留 8 GB，实际需求随缓存变化。软件安装包包含下载配置功能，环境按需下载，首次配置需要网络。

上游来源和缓存说明见 [Lean 发布页](https://github.com/leanprover/lean4/releases/tag/v4.34.1) 与 [Mathlib 项目指南](https://leanprover-community.github.io/install/project.html)。

研究完成要求登记的 Lean 目标已验证，并且研究文档中保存了非空的自然语言证明。模型遗漏正文时，软件最多进行三轮针对性的补写；仍未写入时会明确提示缺失内容，并保留 Lean 验证证据。正文质量和含义忠实性仍需人工审阅。
