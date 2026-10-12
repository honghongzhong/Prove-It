# 第三方许可说明

[English](THIRD_PARTY_NOTICES.md) · 简体中文

- Electron：MIT；桌面发行包包含 Electron 和 Chromium 的许可证。
- Python：PSF 及所带组件的许可证，后端发行包中的 Python-LICENSE.txt。
- PyInstaller 启动器：带分发例外条款的 GPL，见 PyInstaller-LICENSE.txt。
- KaTeX 0.16.22：MIT，见 ui/vendor/katex/LICENSE。
- Noto Sans SC Variable / Fontsource 5.3.1：SIL Open Font License，见 ui/vendor/noto-sans-sc/LICENSE。

Lean、Mathlib 和 Codex 为独立安装工具，不随安装包分发；各自许可及账号条款独立适用。构建依赖记录在 package-lock.json 和 requirements-build.txt。

许可证原文保持原样，不以翻译替代具有法律效力的原文。本文件只是双语说明。

环境管理按需下载官方 Lean、Mathlib，以及必要时的 Git for Windows MinGit，未将这些组件嵌入 ProveIt 安装包。下载和解压内容保留上游许可证文件，各组件的上游许可独立适用。
