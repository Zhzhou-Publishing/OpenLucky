// Tool window registry — the single declaration source for tool windows.
//
// Mirrors the backend-contract philosophy: one place declares every tool's
// view, size and payload shape. The window manager (app/main/tool-windows.js)
// reads this to size the child window; the renderer reads `view` to decide
// which component to mount for `?tool=<name>`. pr/025.tool_windows.md
const TOOLS = {
  dust: {
    view: 'DustTool',
    width: 1000,
    height: 800,
    child: true,
    // Context passed to the tool window when it is opened (pull via
    // get-tool-context). The dust window edits a single photo's working copy
    // and carries the photo's current processing params so its preview can run
    // the full pipeline (apply-filmparam) faithfully.
    payload: {
      photo: 'string',
      workingDir: 'string',
      outputDir: 'string',
      params: 'string',
      rotateClockwise: 'number',
      area: 'null | obj',
      areaBasis: 'null | obj',
      exposure: 'number',
      whiteBalance: 'string',
      tone: 'string',
      colorMode: 'string',
      dust: 'null | obj'
    }
  }
}

module.exports = { TOOLS }
