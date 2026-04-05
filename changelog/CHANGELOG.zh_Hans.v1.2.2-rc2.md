# OpenLucky v1.2.2-rc2 发布说明

## 摘要
此版本引入了全面的国际化（i18n）支持，使应用程序能够支持简体中文和英语两种语言。用户现在可以在语言之间动态切换，所有 UI 组件均已本地化。

## 变更

### 新功能
- **添加国际化支持**：为整个应用程序实现了 vue-i18n 以提供全面的多语言支持
- **创建语言切换器组件**：添加了 LanguageSwitcher 组件，允许用户在简体中文和英语（美国）之间切换
- **本地化所有 UI 页面**：所有用户界面元素现在都支持两种语言，包括：
  - 导航栏（首页、关于）
  - 照片目录页面（标题、描述、按钮、错误消息）
  - 照片库页面（导航、刷新按钮、图片计数、加载状态、空状态）
  - 照片编辑页面（导航、操作标签、按钮、加载状态、空状态）
  - 底部菜单（预设标签、应用按钮状态）
  - 关于页面（标题、版本信息、描述、技术列表）

### 增强
- **语言持久化**：用户语言偏好设置保存到 localStorage，并在会话之间保持
- **语言选择界面**：在导航栏中添加了语言切换器以便于访问
- **语言文件结构**：实现了翻译文件的清晰分离（en_US.js、zh_Hans.js）以便于维护
- **版本更新**：将应用程序版本更新至 v1.2.2-rc2 以反映新功能
- **Inno Setup 脚本更新**：更新安装程序脚本版本以匹配应用程序版本

### 依赖项
- **添加 vue-i18n**：添加了 vue-i18n 11.3.0 版本以支持国际化
- **添加 i18n 依赖项**：添加了 vue-i18n 功能所需的 @intlify/* 包

## 技术细节

### 新文件
- `app/src/i18n/index.js`：主要的 i18n 配置文件
- `app/src/locales/en_US.js`：英文翻译文件，包含所有 UI 字符串
- `app/src/locales/zh_Hans.js`：简体中文翻译文件，包含所有 UI 字符串
- `app/src/components/LanguageSwitcher.vue`：语言选择组件

### 修改文件
- `app/src/main.js`：将 i18n 插件集成到 Vue 应用程序中
- `app/src/components/Navbar.vue`：添加了 LanguageSwitcher 组件和 i18n 键路由
- `app/src/components/BottomMenuBar.vue`：用 i18n 键替换了硬编码字符串
- `app/src/pages/About.vue`：为所有内容实现了 i18n
- `app/src/pages/PhotoDirectory.vue`：为所有内容实现了 i18n
- `app/src/pages/PhotoGallery.vue`：为所有内容实现了 i18n，包括动态图片计数
- `app/src/pages/PhotoEdit.vue`：为所有内容实现了 i18n
- `app/package.json`：更新版本并添加了 vue-i18n 依赖
- `app/package-lock.json`：更新了包含新依赖项的锁文件
- `app/yarn.lock`：更新了包含新依赖项的锁文件
- `OpenLucky.iss`：更新版本至 v1.2.2-rc2

### 翻译覆盖
所有面向用户的文本元素都已翻译，包括：
- 导航和路由
- 按钮标签和操作
- 加载和空状态
- 错误消息和警告
- 表单标签和输入占位符
- 页面标题和描述
- 操作按钮（应用、全部应用、返回、刷新）

## 语言支持
- **简体中文**：zh_Hans - 默认语言
- **英语**：en_US - 具有完全支持的备选语言

## 兼容性
- 需要 vue-i18n 11.3.0
- 与现有功能保持向后兼容
- 存储在 localStorage 中的语言偏好设置需要浏览器存储支持
