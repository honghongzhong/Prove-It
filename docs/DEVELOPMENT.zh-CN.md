# 开发与发布

[English](DEVELOPMENT.md) · 简体中文

源码模式需要 Python 3.11+、Lean 4 和已登录的 Codex CLI。运行 `python app.py` 后打开 http://127.0.0.1:8765。

## Windows 桌面构建

使用 Node.js 22+ 和 Python 3.13 x64：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
npm ci
npm start
npm run dist
```

产物在 dist/。安装包包含 Python 和界面资源，不包含 Lean、Codex、Mathlib 或用户工作区。按用户安装，卸载保留研究。当前发行包未签名。

## 验证

```powershell
python -m unittest discover -s tests -v
node tests/test_export.mjs
python tools/smoke_backend.py build/backend/proveit-backend/proveit-backend.exe
python tools/check_docs.py
python tools/release_audit.py
```

冒烟测试使用临时空白工作区和真实 Lean。隐私检查前先暂存拟公开文件；不要发布本地日志或冒烟报告。

检查 Electron 启动时，将 PROVEIT_DESKTOP_DATA_DIR 设为空白临时目录，PROVEIT_SMOKE_REPORT 设为临时 JSON 路径，再运行打包的 ProveIt.exe。程序写入健康报告和截图后退出。这是测试入口，不是遥测。

测试、安装包启动与隐私审查通过后才发布。附件为 Setup、ZIP 和 SHA256SUMS.txt。保留提交历史，不要强制推送。遵循[语言规范](LANGUAGE_POLICY.zh-CN.md)。

参考：[Electron 安全](https://www.electronjs.org/docs/latest/tutorial/security)、[NSIS](https://www.electron.build/docs/nsis/)、[Codex App Server](https://learn.chatgpt.com/docs/app-server)。

## 模型来源回归测试

`python -m unittest discover -s tests -v` 使用本地 HTTP Chat Completions 服务执行研究工具，再调用实际安装的 Lean，并禁止启动 Codex。其它测试覆盖 DPAPI 密钥加解密、密钥清除及设置接口隔离、地址验证、暂停时丢弃返回响应、删除项目分组后保留研究。测试无需付费 API 凭据。

桌面冒烟模式使用 `PROVEIT_SMOKE_REPORT` 和隔离的 `PROVEIT_DESKTOP_DATA_DIR`，记录启动引导、模型来源表单显示、密码字段类型、横向溢出和截图。在隔离配置目录的 `toolchain.json` 中将 `CODEX_EXE` 指向不存在的文件，可测试首次启动提示。为让 Chromium 完成绘制，截图钩子会短暂显示测试窗口。`python tools/smoke_backend.py build/backend/proveit-backend/proveit-backend.exe --codex` 独立检查冻结后端及真实 Lean。模型目录和账户检测只证明传输及登录状态，不证明实际推理权限。

## 管理环境测试

环境回归覆盖压缩包路径穿越和链接拒绝、本地 HTTP 续传和校验失败、取消、超时进程清理、仅限管理项目的 Git 锁恢复、Windows 代理继承、本地 curl 限制、模型选环境但不代替目标审阅，以及已有 Codex 会话的工具架构升级。`tools/test_environment_setup.py core` 或 `mathlib` 在 `PROVEIT_DATA_DIR` 执行真实安装；`PROVEIT_ENV_IGNORE_SYSTEM=1` 会跳过系统安装发现，用于从零下载测试。这些测试下载较大的公开文件，应使用隔离目录。桌面冒烟模式还支持 `PROVEIT_SMOKE_ENV=1`，通过实际界面操作环境管理和核心安装。全量 `import Mathlib` 可能较慢，安装检查使用 `Mathlib.Data.Nat.Prime.Defs` 和经过实际验证的素数定理。
