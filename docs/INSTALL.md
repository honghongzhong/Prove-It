# 安装 / Installation

## Windows x64

1. 从 [官方项目发布页](https://github.com/honghongzhong/Prove-It/releases/latest) 下载 Setup EXE，运行安装向导；或完整解压 ZIP 后运行 ProveIt.exe。无需管理员权限或单独安装 Python。
2. 按 [Lean 官方安装指南](https://lean-lang.org/install/) 安装 Lean 4 / Elan。新终端运行 `lean --version` 和 `lake --version`，两者应正常返回版本。
3. 安装 [Codex CLI](https://github.com/openai/codex)。使用 npm 时先安装 Node.js，再运行：

```powershell
npm install -g @openai/codex
codex --version
codex login
```

4. 登录完成后重新启动 ProveIt。在对话输入框底部等待模型列表加载。模型权限、费用与限额取决于你自己的 Codex 账号和配置。
5. 新建研究，按照使用手册的小例子检查 Lean 与 Codex。仅安装应用不表示工具链已就绪。

当前安装包没有代码签名证书，系统可能提示未知发布者。校验文件：

```powershell
Get-FileHash .\ProveIt-0.5.0-windows-x64-setup.exe -Algorithm SHA256
```

与发布附件 `SHA256SUMS.txt` 比较。

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

安装包不捆绑 Mathlib。使用自己的、依赖已准备好的 Lake 项目，在 Lean 页添加其路径并选择该环境。可按 [Mathlib 文档](https://github.com/leanprover-community/mathlib4) 准备工程；在项目目录确认 `lake env lean --version` 工作正常。使用项目锁定的 Lean 版本，不要手动替换为不匹配的编译器。

## 排错

- 模型列表失败：终端检查 `codex --version`、`codex login status`；确认当前账号可使用模型，然后重启或点击重试。
- 找不到 Lean：检查 PATH 或 toolchain.json；源码树并不等于已安装编译器。
- 导入 Mathlib 失败：选择对应 Lake 项目，准备其依赖；核心 Lean 环境不自动提供 Mathlib。
- 已有活动写入者：新版在明确的会话占用冲突下保留本地研究，并创建带工具的新工作会话；不会终止其他客户端。认证、网络等错误不会被当成写入冲突掩盖。
- 无法启动：检查 toolchain.json 是否为有效 JSON，关闭同一工作区的其他实例；不要删除 workspace.sqlite3 以尝试修复。
- 更新：退出应用后运行新安装包。研究数据留在用户目录；重要研究先备份。没有自动更新服务。

## English quick start

Install the Windows x64 Setup or extract the complete ZIP. Python is bundled. Install native Windows Lean/Elan and Codex CLI separately, log in with `codex login`, then restart ProveIt. Use the Alt menu to open the data folder and configure toolchain.json for custom executable paths. Mathlib requires a separately prepared Lake project. The release is unsigned; verify SHA256SUMS.txt. No macOS/Linux installer is included.
