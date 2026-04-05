# OpenLucky v1.2.2-rc1 发布说明

## 摘要
此版本包含多个错误修复和功能改进，主要聚焦于目录处理、预设同步和临时文件管理。

## 变更

### 错误修复
- **修复页面标题显示**：PhotoGallery 和 PhotoEdit 页面现在会在标题中显示选择的原始目录名称，而不是工作目录名称，提供更好的用户上下文
- **修复 affectedImages 移除逻辑**：更正了成功应用胶片参数后 affectedImages 集合未被正确清除的问题，通过从后端响应中正确提取文件名来实现
- **修复 filmparam 输出路径问题**：解决了应用程序使用目录路径而非正确文件路径的问题
- **改进临时文件清理**：使用 tmp.dirSync 替代手动文件系统操作，确保应用程序退出时一致地清理临时文件，防止在系统临时目录中累积

### 新功能
- **实现临时目录重构**：将临时目录处理从 PhotoGallery 移至 PhotoDirectory，实现更好的关注点分离
- **添加 .preset.json 同步**：实现从工作目录将 .preset.json 复制回原始目录的功能，确保用户设置被保留
- **支持 preset.json 中的 output_dir**：增强全分辨率图像加载功能，支持从 preset.json 中指定的输出目录加载处理后的图像
- **添加 prepare-working-directory IPC 处理程序**：创建新的 IPC 处理程序以改进临时目录管理

### 改进
- **添加 standard-version**：集成 standard-version 以实现自动化的 changelog 生成
- **重构 openlucky.py**：移除未使用的 filmbytes 命令处理逻辑，并修复 film 命令中的配置文件读取
- **改进预设应用期间的用户反馈**：在 PhotoGallery 中预设应用期间添加了沙漏光标并禁用缩略图，以提供更好的视觉反馈
- **保持向后兼容性**：确保现有路由与新的目录处理方法一起工作

## 技术细节

### 后端变更
- 更新 PhotoDirectory IPC 处理程序以支持 prepare-working-directory-from-selected
- 添加 copy-preset-json IPC 处理程序以实现同步
- 修改 get-full-res-image 以支持 output_dir 参数
- 移除硬编码的工作临时目录逻辑，改用 tmp.dirSync

### 前端变更
- PhotoGallery：更新标题计算以使用 originalDirectoryPath 而不是 workingDirectory
- PhotoEdit：更新标题计算以使用 originalDirectory 而不是 workingDirectory
- PhotoEdit：修复 affectedImages 逻辑，正确从后端响应中提取文件名
- 两个页面：添加预设应用操作后的 preset.json 同步调用

## 兼容性
- 与现有路由向后兼容
- 需要更新后的 Electron main.js 以支持新的 IPC 处理程序
