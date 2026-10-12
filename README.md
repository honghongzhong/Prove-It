# ProveIt

**面向数学研究者的 AI 辅助工作台 · An AI-assisted mathematical research workspace**

[下载安装包 / Download](https://github.com/honghongzhong/Prove-It/releases/latest) · [安装说明](docs/INSTALL.md) · [使用手册](docs/USAGE.md) · [English](docs/README.en.md) · [构建与发布](docs/DEVELOPMENT.md)

ProveIt 连接 **Codex** 的研究与编码能力和 **Lean 4** 的形式化检查。研究者提出问题、澄清假设、指明方向；AI 保存目标、分解步骤、修订自然语言论证与 Lean 代码，并根据真实诊断继续迭代。

![ProveIt desktop workspace](docs/assets/workspace.png)

## 下载与启动

Windows x64 用户从 [Releases](https://github.com/honghongzhong/Prove-It/releases) 下载 `ProveIt-*-windows-x64-setup.exe`。也提供 ZIP 免安装版：完整解压后运行 `ProveIt.exe`，不要单独移动 EXE。

安装包内置 Electron 与 Python 后端，**无需另装 Python**。需要自行安装 **Lean 4 / Elan** 和 **已登录的 Codex CLI**。Mathlib 是可选的外部 Lake 项目。安装与排错见 [INSTALL.md](docs/INSTALL.md)。当前发布 Windows x64；未发布 macOS / Linux 桌面安装包。

本版未使用代码签名证书，Windows 可能显示未知发布者提示。请核对本仓库发布页及 SHA-256；不要关闭系统安全防护。ProveIt 不是 OpenAI 或 Lean 的官方产品。

## 工作区

- **项目侧栏**：创建、重命名、搜索和归类研究，回收站可恢复删除的研究。
- **对话**：选择模型及思考深度，实时查看回复与穿插的工具调用；随时补充方向、暂停或继续。
- **研究**：自然语言目标、假设、完整形式化目标、证明路线和正文；独立人工审阅状态。
- **Lean**：源码、环境、真实检查、诊断及与当前产物绑定的证据。
- **导出**：Lean 源码、排版 Markdown、包含修订历史的 JSON。
- **显示**：中英文、黑白双主题、本地字体与 KaTeX 公式渲染。

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

打开 http://127.0.0.1:8765 。桌面开发和安装包构建见 [开发说明](docs/DEVELOPMENT.md)。

## 验证边界

只有实际运行 Lean、完整登记目标类型成立、公理依赖通过审计，才标记形式目标已验证。局部引理、有限实例和候选编译成功不会替代完整目标。拒绝 `sorryAx` 和额外公理；接受的常用基础公理为 `propext`、`Classical.choice`、`Quot.sound`。修改源码、目标或环境会使旧证据过期。

**Lean 验证编码后的命题，不验证自然语言翻译的忠实性、假设的合理性、研究的新颖性或意义。** 这些由研究者审阅。ProveIt 不保证 AI 能解决提出的数学问题。

## 数据与隐私

桌面版研究保存在 `%APPDATA%/ProveIt/workspace`，与安装目录分开；源码版默认保存在仓库本地 `proofs/` 与 `.proveit/`。详细备份与迁移见使用手册。

仓库和安装包不包含作者的研究、聊天、账号、数据库、日志、Lean/Mathlib 工作目录或 Codex 凭据。`.gitignore`、安装包资源白名单和发布检查共同限制发布内容。

Codex 会接收你主动提交的研究及相关上下文，并按你自己的账号、模型提供方和配置处理。ProveIt 本身不增加遥测，也不收集登录密码。Lean 元编程、Lake 项目及 Codex 工具可能执行本机代码：仅用于可信本地研究环境，不是执行不可信代码的安全沙箱；不要公开转发后端端口。

## 贡献与许可证

欢迎通过 [Issues](https://github.com/honghongzhong/Prove-It/issues) 提交复现步骤，上传前删除研究内容、令牌和本地路径。贡献流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。

沿用仓库原有 [MIT License](LICENSE)。依赖许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
