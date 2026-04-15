# Electron 开发调试模式使用说明

## 开启调试模式

### 方式一：完整热重载开发（推荐）
```bash
npm run dev:hot
```
这个命令会：
1. 启动 Vite 开发服务器
2. 启动 Electron 应用
3. 自动打开开发者工具
4. 监听文件变化并自动重新加载

### 方式二：分别启动
```bash
# 终端1：启动 Vite 开发服务器
npm run dev

# 终端2：启动 Electron 应用
npm run dev:electron
```

### 方式三：仅启动 Electron（用于调试已构建的前端）
```bash
npm run electron
```

## 调试功能

### 开发环境自动启用
- ✅ 开发者工具自动打开
- ✅ 代码变化自动热重载
- ✅ 控制台日志输出
- ✅ 网络请求调试
- ✅ 性能分析工具

### 生产环境禁用
- ❌ 开发者工具禁用（提升性能）
- ❌ 热重载禁用（提升性能）
- ✅ 保持所有功能正常运行

## 主要配置变更

### 1. webPreferences 配置
```javascript
webPreferences: {
  devTools: !app.isPackaged, // 开发环境启用，生产环境禁用
  // ... 其他配置
}
```

### 2. 热重载配置
```javascript
if (!app.isPackaged) {
  const electronReload = require('electron-reload')
  electronReload(__dirname, {
    electron: path.join(__dirname, 'node_modules', '.bin', 'electron'),
    hardResetMethod: 'exit',
    debug: true,
    verbose: true
  })
}
```

### 3. 自动打开开发者工具
```javascript
if (!app.isPackaged) {
  win.webContents.openDevTools()
}
```

## 调试技巧

### 1. 控制台调试
- 打开的开发者工具包含完整的控制台
- 可以使用 `console.log()` 输出调试信息
- 支持断点调试和单步执行

### 2. 网络调试
- Network 标签查看所有 HTTP 请求
- 可以检查请求和响应数据
- 支持网络性能分析

### 3. 性能分析
- Performance 标签分析应用性能
- Memory 标签检查内存使用情况
- 可以识别性能瓶颈

### 4. 元素检查
- Elements 标签检查 HTML/CSS
- 可以实时修改样式
- 查看组件结构

## 热重载说明

### 支持的文件变化
- ✅ main.js - Electron 主进程（需要重启）
- ✅ src/ 目录下的 Vue 组件
- ✅ index.html
- ✅ 样式文件

### 注意事项
- main.js 变化会触发 Electron 重启
- Vue 组件变化会热更新（保留状态）
- 样式变化会立即反映

## 环境变量

### 开发环境标识
```javascript
!app.isPackaged // 返回 true 表示开发环境
```

### 使用示例
```javascript
if (!app.isPackaged) {
  console.log('开发环境')
  // 开发环境特定代码
} else {
  console.log('生产环境')
  // 生产环境特定代码
}
```

## 常见问题

### Q: 热重载不工作？
A: 确保：
1. 使用 `npm run dev:hot` 启动
2. 确认 electron-reload 正确安装
3. 检查控制台是否有错误信息

### Q: 开发者工具不自动打开？
A: 检查：
1. 确认在开发环境下运行
2. 检查 main.js 中的 `win.webContents.openDevTools()` 是否被执行

### Q: 如何禁用某个调试功能？
A: 在 main.js 中找到对应代码并注释掉：
```javascript
// if (!app.isPackaged) {
//   win.webContents.openDevTools()
// }
```

## 性能优化

开发环境 vs 生产环境对比：
- 开发环境：启用调试工具，功能完整但性能较低
- 生产环境：禁用调试工具，性能优化

生产环境自动应用的优化：
- ❌ 禁用开发者工具
- ❌ 禁用热重载
- ❌ 禁用详细日志
- ✅ 保持所有业务功能正常