# 本地 DOCX 渲染器

本工作区已部署 LibreOffice 26.2.4.2，并修复 Codex 自带 `render_docx.py` 在 Windows 下生成错误用户配置 URI、找不到 Poppler 的问题。

## 使用方法

```powershell
.\render_docx_local.cmd "输入文档.docx" ".\渲染输出目录" --emit_pdf
```

输出目录包含逐页 PNG 和同名 PDF。主入口为 `render_docx_local.cmd`；`render_docx_windows.py` 负责注入本地 LibreOffice、正确的 Windows 文件 URI 与 Poppler 路径。

本地 LibreOffice 位于：

```text
C:\Users\Administrator\Documents\Codex\2026-07-21\h\tools\LibreOffice\program\soffice.exe
```

该目录也已写入当前用户的 `PATH`。已打开的终端不会自动刷新环境变量，但上述 `.cmd` 无需重启即可直接运行。
