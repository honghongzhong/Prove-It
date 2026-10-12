# 安装 / Installation

[English](INSTALL.md) · 简体中文

## Windows x64

1. 从 [官方项目发布页](https://github.com/honghongzhong/Prove-It/releases/latest) 下载 Setup EXE，运行安装向导；或完整解压 ZIP 后运行 ProveIt.exe。无需管理员权限或单独安装 Python。
2. 启动 ProveIt，在设置中选择自定义兼容 API（密钥、Base URL、模型）或 Codex；API 模式无需安装 Codex。
3. 点击侧栏 **Lean 环境**，选择 **Lean 核心** 或 **Mathlib**，点击 **安装 / 检查**。已有匹配安装会被复用，缺失组件自动下载，无需管理员权限，也不修改系统默认工具链。研究工具及证明检查默认允许自动配置环境。
4. 等待真实 Lean 检查通过后开始研究。环境管理显示进度、日志、取消和重试入口，设置中可以填写下载代理。首次下载需要网络和数 GB 磁盘空间。

若选择 Codex，安装 [Codex CLI](https://github.com/openai/codex)。使用 npm 时先安装 Node.js，再运行：

```powershell
npm install -g @openai/codex
codex login
```

在设置中点击 **保存并测试连接**。软件自行建立工作会话，无需在 Codex 中另建项目。模型权限及 API 费用取决于相应服务商。

当前安装包没有代码签名证书，系统可能提示未知发布者。校验文件：

```powershell
Get-FileHash .\ProveIt-0.7.0-windows-x64-setup.exe -Algorithm SHA256
```

与发布附件 `SHA256SUMS.txt` 比较。

新安装默认使用 **English**，可在 Settings 中切换为中文；已有用户保存的语言选择保持不变。安装向导的语言选择框也默认英文，并提供中文。

## 工具不在 PATH

按 Alt 显示桌面菜单，选择 **ProveIt → Open data folder / 打开数据目录**。在该目录新建 `toolchain.json`，仅填写需要覆盖的本机路径，然后重启：

```json
{
  "LEAN_EXE": "C:/Tools/elan/bin/lean.exe",
  "LAKE_EXE": "C:/Tools/elan/bin/lake.exe",
  "CODEX_EXE": "C:/Tools/codex/codex.exe"
}
```

路径是示例，必须换成真实安装位置，不要填写账号或令牌。桌面版自动搜索当前 PATH、用户 `.elan/bin`、`.cargo/bin` 和 npm 全局程序目录。只装在 WSL 中的程序不是 Windows 可执行文件；本安装包需要 Windows 工具链。

## Mathlib

环境管理按需下载 Mathlib、匹配的 Lean、依赖和编译缓存；预设将 Lean/Mathlib 配套固定为 v4.34.1。软件编译代表性的 Mathlib 定理来检查环境，这与研究目标验证分开。仍可通过 **添加 Lean 环境** 注册自己的 Lake 项目并在 Lean 页选择，已有项目不会被修改。详见 [Mathlib 文档](https://github.com/leanprover-community/mathlib4)。

## 排错

- 模型列表失败：终端检查 `codex --version`、`codex login status`；确认当前账号可使用模型，然后重启或点击重试。
- 找不到 Lean：先用环境管理安装 / 检查 Lean 核心；如手动覆盖的 toolchain.json 路径无效，应修正或移除覆盖项；源码树并不等于已安装编译器。
- 导入 Mathlib 失败：选择对应 Lake 项目，准备其依赖；核心 Lean 环境不自动提供 Mathlib。
- 已有活动写入者：新版在明确的会话占用冲突下保留本地研究，并创建带工具的新工作会话；不会终止其他客户端。认证、网络等错误不会被当成写入冲突掩盖。
- 无法启动：检查 toolchain.json 是否为有效 JSON，关闭同一工作区的其他实例；不要删除 workspace.sqlite3 以尝试修复。
- 更新：退出应用后运行新安装包。研究数据留在用户目录；重要研究先备份。没有自动更新服务。
