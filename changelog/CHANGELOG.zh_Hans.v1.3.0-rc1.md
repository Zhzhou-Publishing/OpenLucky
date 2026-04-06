# OpenLucky v1.3.0-rc1

## 新功能

### 保存全部功能
- 在底部菜单栏添加保存全部按钮（天蓝色，位于应用预设按钮右侧）
- 实现单文件预设应用（apply-preset-to-file）
- 实现批量预设应用（apply-preset-to-batch）
- 添加全局状态管理 isSaveAllClicked
- 为所有保存全部按钮添加红点指示器，由 isSaveAllClicked 状态控制
- 添加 Ctrl+S 键盘快捷键用于保存全部
- 在保存全部过程中禁用所有控件
- 使用 isApplyingAll 优化 PhotoEdit 页面按钮禁用状态，用于批量操作
- 添加 isSaveAllClicked 状态变更日志记录

### 预览功能
- 实现预览功能，输入变更后有 5 秒防抖延迟
- 添加 applyPreview 函数（不包含 isApplying 逻辑）
- 添加预览状态管理（isPreviewing, previewingImages, presetLoaded）
- 在 NumberInput 组件中添加键盘事件处理
- 添加预览状态的国际化翻译（中文和英文）
- 更新缩略图加载状态，用于预览中的图片
- 在预览过程中禁用应用/应用全部按钮和输入字段

### 图片缩放工具
- 添加图片缩放工具，支持多种格式和缩放模式
- 使用 openlucky 工具的 resize 命令改进图片缩放逻辑
- 在 PhotoDirectory 和 PhotoGallery 中添加 outputDirectory 处理

### 代码质量与维护
- 在 Electron 主进程中添加 openlucky 命令执行日志记录
- 将图片格式常量提取到单独的文件以提高可维护性
  - 创建 app/src/constants/imageFormats.js，包含 IMAGE_EXTENSIONS, RAW_EXTENSIONS, TIFF_FORMATS
  - 创建 cmd/constants/image_formats.py，包含对应的常量
- 从所有 Python 文件中移除未使用的导入
- 更新所有文件以使用集中化的格式常量
- 将 globalState 转换为 Vue 响应式对象以实现即时 UI 更新

## Bug 修复

- 使用 async/await 和正确的 Sharp API 修复 sharp.sync 错误
- 从 PhotoEdit 返回到 PhotoGallery 时保留目录参数
- 从应用操作中移除 .preset.json 复制功能

## 改进

- 重构使得在代码库中维护和更新支持的图片格式更加容易
- 在保存全部和预览操作期间增强用户反馈
- 改进按钮状态管理以提供更好的用户体验
