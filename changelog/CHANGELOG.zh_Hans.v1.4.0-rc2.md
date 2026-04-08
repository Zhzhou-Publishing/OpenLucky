# 更新日志

## v1.4.0-rc2 (2026-04-08)

### Bug 修复
- **中文文件路径支持**: 修复了在 Windows 上处理包含中文字符的文件时的编码问题
  - 添加 `read_image_safe()` 函数，使用 `np.fromfile` + `cv2.imdecode` 读取图片
  - 添加 `write_image_safe()` 函数，使用 `np.tofile` 写入图片
  - 在 tool resize 命令中用 `read_image_safe()` 替换 `cv2.imread()` 以支持 Unicode 路径
  - 解决了 Windows 命令行中的非 ASCII 文件路径编码问题

### 技术变更
- 增强 `lib/tool/resize.py` 的安全文件 I/O 操作
- 改进文件路径处理的跨平台兼容性

---

## 安装

对于使用安装程序的 Windows 用户，只需运行 `openlucky-setup.exe` 文件并按照安装向导进行操作。

对于开发或手动安装，请参考项目文档。

---

## 升级说明

此版本修复了一个关键错误，即 `tool resize` 命令在 Windows 上无法处理路径中包含中文字符的文件。使用中文文件路径的用户现在应该能够无编码问题地使用所有功能。

---

## 已知问题

- 此版本没有已知问题

---

## 贡献者

- Ares

---

## 链接

- [GitHub 仓库](https://github.com/Zhzhou-Publishing/OpenLucky)
- [问题追踪](https://github.com/Zhzhou-Publishing/OpenLucky/issues)
