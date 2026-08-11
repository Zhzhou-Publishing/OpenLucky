// Window manager for tool windows (dust now, scratch + others later).
//
// Tools open as CHILD windows of the main window: always on top of it, and on
// Windows the main window is locked while a tool is open — accepted product
// behaviour (pr/025.tool_windows.md). A tool is a singleton: at most one window
// per tool, and re-opening does not focus an existing one (the parent is locked
// anyway, so the user path is close-then-reopen).
//
// Context flows in/out via the contract entries:
//   open-tool-window  {tool, payload} → creates the child window
//   get-tool-context  {}              → the payload this window was opened with
//   tool-result       {tool, result}  → forwarded to the owning (main) window
const { BrowserWindow } = require('electron')
const { TOOLS } = require('../shared/tools')

const windows = new Map()   // tool -> { win, payload, ownerWinId }

function openToolWindow(tool, payload, ownerWin) {
  const spec = TOOLS[tool]
  if (!spec) throw new Error(`unknown tool "${tool}"`)
  if (windows.has(tool)) return null   // singleton: no second window, no focus
  if (!ownerWin || ownerWin.isDestroyed()) {
    throw new Error('open-tool-window: no usable owner window')
  }

  const win = new BrowserWindow({
    parent: ownerWin,
    width: spec.width,
    height: spec.height,
    show: false,
    autoHideMenuBar: true,
    resizable: true,
    webPreferences: {
      devTools: true,
      spellCheck: false,
      enableWebSQL: false,
      offscreen: false,
      nodeIntegration: true,
      contextIsolation: false
    }
  })

  win.loadFile('dist/index.html', { query: { tool } })
  win.once('ready-to-show', () => win.show())

  windows.set(tool, { win, payload, ownerWinId: ownerWin.id })
  win.on('closed', () => windows.delete(tool))
  return win.id
}

// Payload the calling tool window was opened with, or null if not a tool.
function getToolContext(sender) {
  for (const rec of windows.values()) {
    if (rec.win.webContents === sender) return rec.payload
  }
  return null
}

// Forward a tool window's result to the window that opened it (the main
// window), which merges it into the photo's params and refreshes.
function forwardToolResult(tool, result) {
  const rec = windows.get(tool)
  if (!rec) return
  const owner = BrowserWindow.fromId(rec.ownerWinId)
  if (owner && !owner.isDestroyed()) {
    owner.webContents.send('tool-result', { tool, result })
  }
}

module.exports = { openToolWindow, getToolContext, forwardToolResult }
