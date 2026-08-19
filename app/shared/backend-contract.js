// Shared backend contract — the single source of truth for every IPC command.
//
// JSON-serializable plain data ONLY (no functions, no comments, double-quoted
// strings, no trailing commas) so it round-trips through JSON.parse/stringify
// unchanged. That round-trip is enforced by a conformance test and proves the
// table is serde-ready for the planned Tauri/Rust port (include_str! + serde).
//
// The main-process engine (app/ipc/engine.js) drives ipcMain registration from
// this table; the renderer facade (app/src/services/backend/) maps each id to a
// method; the Rust side later reads the same table to emit byte-identical argv.
//
// Fields:
//   id             matches app/ipc/<id>.js filename (test-enforced)
//   kind           'spawn-json' | 'spawn-stream' | 'custom'
//   registration   ipcMain method: 'handle' | 'on' | 'once'
//   channel        the ipcMain registration channel string
//   label          logger scope (createLogger scope)
//   payload        { type, props } — 'object'|'positional'|'single'|'none'
//   return         for spawn-json: what the handle resolves to
//   emit           for spawn-stream/custom: { started, progress, success, error, push }
//   spawn          argv blueprint: cliBuilder name, command, stdio, notes
//   implementation 'engine-driver' | 'custom-handler'
//   capabilities   what the Rust side must reimplement natively
module.exports = [
  {
    "id": "compute-histogram",
    "kind": "spawn-json",
    "registration": "handle",
    "channel": "compute-histogram",
    "label": "ComputeHistogram",
    "payload": {
      "type": "object",
      "props": {
        "directoryPath": "string",
        "filename": "string",
        "downsampling": "number?=256",
        "area": "null | {x1,y1,x2,y2:number}?=null"
      }
    },
    "return": {
      "type": "object",
      "note": "JSON.parse(stdout); rejects on non-zero exit / spawn error / parse error"
    },
    "emit": {},
    "spawn": {
      "cliBuilder": "buildHistogramArgs",
      "command": "tool histogram",
      "prefix": "resolveOpenLuckyCommand",
      "stdio": ["pipe", "pipe", "pipe"],
      "windowsHide": true,
      "note": "input = resolveImagePath(directoryPath, filename, readPresetJson(directoryPath))"
    },
    "implementation": "engine-driver",
    "capabilities": ["spawn", "fs-read"]
  },
  {
    "id": "pick-color",
    "kind": "spawn-json",
    "registration": "handle",
    "channel": "pick-color",
    "label": "PickColor",
    "payload": {
      "type": "object",
      "props": {
        "filePath": "string",
        "x": "number",
        "y": "number",
        "format": "string?=8"
      }
    },
    "return": {
      "type": "object",
      "note": "JSON.parse(stdout); rejects on non-zero exit / spawn error / parse error"
    },
    "emit": {},
    "spawn": {
      "cliBuilder": "buildPickArgs",
      "command": "tool pick",
      "prefix": "resolveOpenLuckyCommand",
      "stdio": ["pipe", "pipe", "pipe"],
      "windowsHide": true,
      "note": ""
    },
    "implementation": "engine-driver",
    "capabilities": ["spawn"]
  },
  {
    "id": "apply-filmparam",
    "kind": "spawn-stream",
    "registration": "on",
    "channel": "apply-filmparam",
    "label": "ApplyFilmparam",
    "payload": {
      "type": "object",
      "props": {
        "inputPath": "string",
        "outputPath": "string",
        "filename": "string",
        "params": "string",
        "rotateClockwise": "number?=0",
        "area": "null | obj?=null",
        "areaBasis": "null | obj?=null",
        "exposure": "number?=null",
        "whiteBalance": "string?=null",
        "tone": "string?=null",
        "colorMode": "string?=null",
        "dust": "null | obj?=null",
        "dustRois": "null | array?=null"
      }
    },
    "return": {},
    "emit": {
      "started": { "channel": "filmparam-apply-started", "payload": { "message": "string" } },
      "progress": { "channel": "filmparam-apply-progress", "payload": { "data": "string" } },
      "success": { "channel": "filmparam-apply-success", "payload": { "message": "string", "outputFile": "string" } },
      "error": { "channel": "filmparam-apply-error", "payload": { "message": "string", "error": "string" } }
    },
    "protocol": "started -> progress* -> success | error",
    "spawn": {
      "cliBuilder": "buildFilmparamArgs",
      "command": "filmparam",
      "prefix": "resolveOpenLuckyCommand",
      "stdio": ["pipe", "pipe", "pipe"],
      "windowsHide": true,
      "note": "rotateClockwise default 0 ALWAYS forwarded; input/output = path.join(dir, filename)"
    },
    "implementation": "engine-driver",
    "capabilities": ["spawn"]
  },
  {
    "id": "apply-filmparambatch",
    "kind": "spawn-stream",
    "registration": "on",
    "channel": "apply-filmparambatch",
    "label": "ApplyFilmparambatch",
    "payload": {
      "type": "object",
      "props": {
        "inputPath": "string",
        "outputPath": "string",
        "params": "string",
        "rotateClockwise": "number?=0",
        "area": "null | obj?=null",
        "areaBasis": "null | obj?=null",
        "exposure": "number?=null",
        "whiteBalance": "string?=null",
        "tone": "string?=null",
        "colorMode": "string?=null",
        "dust": "null | obj?=null",
        "dustRois": "null | array?=null"
      }
    },
    "return": {},
    "emit": {
      "started": { "channel": "filmparambatch-apply-started", "payload": { "message": "string" } },
      "progress": { "channel": "filmparambatch-apply-progress", "payload": { "data": "string" } },
      "success": { "channel": "filmparambatch-apply-success", "payload": { "message": "string" } },
      "error": { "channel": "filmparambatch-apply-error", "payload": { "message": "string", "error": "string" } }
    },
    "protocol": "started -> progress* -> success | error",
    "spawn": {
      "cliBuilder": "buildFilmparamArgs",
      "command": "filmparambatch",
      "prefix": "resolveOpenLuckyCommand",
      "stdio": ["pipe", "pipe", "pipe"],
      "windowsHide": true,
      "note": "buildFilmparamArgs with command='filmparambatch'; input/output are dirs (no per-file join)"
    },
    "implementation": "engine-driver",
    "capabilities": ["spawn"]
  },
  {
    "id": "apply-preset",
    "kind": "spawn-stream",
    "registration": "on",
    "channel": "apply-preset",
    "label": "ApplyPreset",
    "payload": {
      "type": "object",
      "props": {
        "inputPath": "string",
        "outputPath": "string",
        "preset": "string"
      }
    },
    "return": {},
    "emit": {
      "started": { "channel": "preset-apply-started", "payload": { "message": "string" } },
      "progress": { "channel": "preset-apply-progress", "payload": { "data": "string" } },
      "success": { "channel": "preset-apply-success", "payload": { "message": "string" } },
      "error": { "channel": "preset-apply-error", "payload": { "message": "string", "error": "string" } }
    },
    "protocol": "started -> progress* -> success | error",
    "spawn": {
      "cliBuilder": "buildFilmbatchArgs",
      "command": "filmbatch",
      "prefix": "resolveOpenLuckyCommand",
      "stdio": ["pipe", "pipe", "pipe"],
      "windowsHide": true,
      "note": "named-preset batch across a directory"
    },
    "implementation": "engine-driver",
    "capabilities": ["spawn"]
  },
  {
    "id": "check-openlucky",
    "kind": "spawn-stream",
    "registration": "on",
    "channel": "check-openlucky",
    "label": "CheckOpenlucky",
    "payload": { "type": "none", "props": {} },
    "return": {},
    "emit": {
      "finalize": { "channel": "openlucky-checked", "payload": { "success": "boolean", "error": "string" } }
    },
    "protocol": "single boolean-status event; no started/progress; stdout not read, stderr is the error string",
    "spawn": {
      "cliBuilder": null,
      "command": "--help",
      "prefix": "resolveOpenLuckyCommand",
      "stdio": ["pipe", "pipe", "pipe"],
      "windowsHide": true,
      "note": "spawns [...prefixArgs, '--help'] to verify the CLI is present"
    },
    "implementation": "engine-driver",
    "capabilities": ["spawn"],
    "finalize": true
  },
  {
    "id": "get-presets",
    "kind": "spawn-stream",
    "registration": "on",
    "channel": "get-presets",
    "label": "GetPresets",
    "payload": { "type": "none", "props": {} },
    "return": {},
    "emit": {
      "finalize": { "channel": "presets-loaded", "payload": { "presets": "array" } },
      "error": { "channel": "presets-error", "payload": { "message": "string", "error": "string" } }
    },
    "protocol": "spawn-json via on: parses config.presets, reshapes each entry with value/label keys",
    "spawn": {
      "cliBuilder": null,
      "command": "config read -f json",
      "prefix": "resolveOpenLuckyCommand",
      "stdio": ["pipe", "pipe", "pipe"],
      "windowsHide": true,
      "note": "spawns [...prefixArgs, 'config', 'read', '-f', 'json']"
    },
    "implementation": "engine-driver",
    "capabilities": ["spawn"],
    "finalize": true
  },
  {
    "id": "apply-preset-to-file",
    "kind": "spawn-stream",
    "registration": "on",
    "channel": "apply-preset-to-file",
    "label": "ApplyPresetToFile",
    "payload": {
      "type": "object",
      "props": {
        "presetFile": "string",
        "inputFilePath": "string",
        "outputFilePath": "string"
      }
    },
    "return": {},
    "emit": {
      "started": { "channel": "preset-to-file-started", "payload": { "message": "string" } },
      "progress": { "channel": "preset-to-file-progress", "payload": { "data": "string" } },
      "success": { "channel": "preset-to-file-success", "payload": { "message": "string" } },
      "error": { "channel": "preset-to-file-error", "payload": { "message": "string", "error": "string" } }
    },
    "protocol": "fs precheck -> resolvePresetKey -> started -> progress* -> success | error; error channel reused for 4 cases",
    "spawn": {
      "cliBuilder": "buildFilmparamArgs",
      "command": "filmparam",
      "prefix": "resolveOpenLuckyCommand",
      "stdio": ["pipe", "pipe", "pipe"],
      "windowsHide": true,
      "note": "buildParamString base 5 fields only; only colorMode forwarded; --rotate-clockwise omitted; coerceRawOutputPath appends .tif for RAW"
    },
    "implementation": "custom-handler",
    "capabilities": ["spawn", "fs", "preset-translate"]
  },
  {
    "id": "apply-preset-to-batch",
    "kind": "spawn-stream",
    "registration": "on",
    "channel": "apply-preset-to-batch",
    "label": "ApplyPresetToBatch",
    "payload": {
      "type": "object",
      "props": {
        "presetFile": "string",
        "inputDir": "string",
        "outputDir": "string"
      }
    },
    "return": {},
    "emit": {
      "progress": { "channel": "preset-to-batch-progress", "payload": { "file": "string", "progress": "string", "data": "string" } },
      "success": { "channel": "preset-to-batch-success", "payload": { "message": "string" } },
      "error": { "channel": "preset-to-batch-error", "payload": { "message": "string", "error": "string" } }
    },
    "protocol": "progress* (synthetic, per file) -> success | error; NO started event; never streams child stdout; handler returns a Promise (tests await it)",
    "spawn": {
      "cliBuilder": "buildFilmparamArgs",
      "command": "filmparam (per file)",
      "prefix": "resolveOpenLuckyCommand",
      "stdio": ["pipe", "pipe", "pipe"],
      "windowsHide": true,
      "note": "sequential awaited loop; resolvePresetKey includeStemVariants; buildParamString includeContrastRgb; forwards ALL preset fields"
    },
    "implementation": "custom-handler",
    "capabilities": ["spawn", "fs", "preset-translate"]
  },
  {
    "id": "confirm-close",
    "kind": "custom",
    "registration": "on",
    "channel": "confirm-close-response",
    "label": "ConfirmClose",
    "payload": { "type": "single", "props": { "allow": "boolean" } },
    "return": {},
    "emit": { "push": { "channel": "confirm-close", "payload": {} } },
    "protocol": "window close intercepted -> push confirm-close -> renderer replies confirm-close-response{allow} -> win.close()",
    "spawn": null,
    "implementation": "custom-handler",
    "capabilities": ["window-close-intercept"],
    "setupWindow": true,
    "moduleState": true
  },
  {
    "id": "copy-preset-json",
    "kind": "custom",
    "registration": "on",
    "channel": "copy-preset-json",
    "label": "CopyPresetJson",
    "payload": {
      "type": "object",
      "props": {
        "workingDirectory": "string",
        "originalDirectory": "string"
      }
    },
    "return": {},
    "emit": {
      "success": { "channel": "copy-preset-json-success", "payload": { "message": "string" } },
      "error": { "channel": "copy-preset-json-error", "payload": { "message": "string" } }
    },
    "protocol": "two early existence guards before fs.copyFileSync; no spawn/sharp",
    "spawn": null,
    "implementation": "custom-handler",
    "capabilities": ["fs"]
  },
  {
    "id": "get-full-res-image",
    "kind": "custom",
    "registration": "on",
    "channel": "get-full-res-image",
    "label": "GetFullResImage",
    "payload": {
      "type": "object",
      "props": {
        "directoryPath": "string",
        "filename": "string"
      }
    },
    "return": {},
    "emit": {
      "success": { "channel": "full-res-image-loaded", "payload": { "url": "string" } },
      "error": { "channel": "full-res-image-error", "payload": { "error": "string" } }
    },
    "protocol": "TIFF transcoded to jpg via sharp (best-effort; falls back to raw file:// path); non-TIFF returns direct file:// url",
    "spawn": null,
    "implementation": "custom-handler",
    "capabilities": ["sharp", "fs", "tmp"]
  },
  {
    "id": "get-images",
    "kind": "custom",
    "registration": "on",
    "channel": "get-images",
    "label": "GetImages",
    "payload": { "type": "single", "props": { "directoryPath": "string" } },
    "return": {},
    "emit": {
      "success": { "channel": "images-loaded", "payload": { "images": "array" } },
      "error": { "channel": "images-error", "payload": "string" }
    },
    "protocol": "sends via event.sender (the calling window); images-error payload is a BARE STRING; manifest-first (readManifest) with disk-scan fallback; entries carry status: ready|pending|error; sharp thumbnails for ready only",
    "spawn": null,
    "implementation": "custom-handler",
    "capabilities": ["sharp", "fs", "tmp", "manifest"]
  },
  {
    "id": "open-external",
    "kind": "custom",
    "registration": "on",
    "channel": "open-external",
    "label": "OpenExternal",
    "payload": { "type": "single", "props": { "url": "string" } },
    "return": {},
    "emit": {},
    "protocol": "validates /^https?:\\/\\//i then shell.openExternal; no emit",
    "spawn": null,
    "implementation": "custom-handler",
    "capabilities": ["shell"]
  },
  {
    "id": "prepare-working-directory",
    "kind": "custom",
    "registration": "on",
    "channel": "prepare-working-directory",
    "label": "PrepareWorkingDir",
    "payload": {
      "type": "positional",
      "props": {
        "directoryPath": "string",
        "options": { "compressPreview": "boolean" }
      }
    },
    "return": {},
    "emit": {
      "progress": { "channel": "processing-progress-update", "payload": { "progress": "string" } },
      "title": { "channel": "window-title-update", "payload": { "title": "string" } },
      "clear": { "channel": "processing-progress-clear", "payload": {} },
      "titleRestore": { "channel": "window-title-restore", "payload": {} },
      "success": { "channel": "working-directory-prepared", "payload": { "workingDirectory": "string", "outputDirectory": "string", "originalDirectory": "string" } },
      "error": { "channel": "working-directory-error", "payload": { "error": "string" } }
    },
    "protocol": "p-limit concurrency max(1, floor(cpus/2)); per-file needsResize -> resizeImage or copy; compressPreview switches resize value to 1920; no cancel handling",
    "spawn": null,
    "implementation": "custom-handler",
    "capabilities": ["fs", "tmp", "p-limit", "spawn"]
  },
  {
    "id": "prepare-working-directory-from-selected",
    "kind": "custom",
    "registration": "on",
    "channel": "prepare-working-directory-from-selected",
    "label": "PrepareWorkingDirFromSelected",
    "payload": {
      "type": "positional",
      "props": {
        "directoryPath": "string",
        "options": { "compressPreview": "boolean" }
      }
    },
    "return": {},
    "emit": {
      "progress": { "channel": "processing-progress-update", "payload": { "progress": "string" } },
      "title": { "channel": "window-title-update", "payload": { "title": "string" } },
      "clear": { "channel": "processing-progress-clear", "payload": {} },
      "titleRestore": { "channel": "window-title-restore", "payload": {} },
      "partialReady": { "channel": "working-directory-partial-ready", "payload": { "workingDirectory": "string", "outputDirectory": "string", "originalDirectory": "string", "readyCount": "number", "total": "number" } },
      "imageReady": { "channel": "working-image-ready", "payload": { "workingDirectory": "string", "name": "string" } },
      "imageError": { "channel": "working-image-error", "payload": { "workingDirectory": "string", "name": "string", "error": "string" } },
      "success": { "channel": "working-directory-from-selected-prepared", "payload": { "workingDirectory": "string", "outputDirectory": "string", "originalDirectory": "string" } },
      "error": { "channel": "working-directory-from-selected-error", "payload": { "workingDirectory": "string", "error": "string" } }
    },
    "protocol": "manifest -> progress*/title* -> partial-ready -> image-ready*/image-error* -> complete; once('cancel-processing') single-flight cancelable; on cancel rmSync working dir + no success/error event",
    "spawn": null,
    "implementation": "custom-handler",
    "moduleState": true,
    "capabilities": ["fs", "tmp", "p-limit", "spawn", "cancel", "manifest"]
  },
  {
    "id": "read-preset-json",
    "kind": "custom",
    "registration": "on",
    "channel": "read-preset-json",
    "label": "ReadPresetJson",
    "payload": { "type": "positional", "props": { "directoryPath": "string" } },
    "return": {},
    "emit": {
      "success": { "channel": "preset-json-loaded", "payload": { "presets": "object" } },
      "error": { "channel": "preset-json-error", "payload": { "error": "string" } }
    },
    "protocol": "trivial passthrough: read .preset.json via shared readPresetJson, send it",
    "spawn": null,
    "implementation": "custom-handler",
    "capabilities": ["fs"]
  },
  {
    "id": "refresh-image",
    "kind": "custom",
    "registration": "on",
    "channel": "refresh-image",
    "label": "RefreshImage",
    "payload": {
      "type": "object",
      "props": {
        "directoryPath": "string",
        "filename": "string"
      }
    },
    "return": {},
    "emit": {
      "success": { "channel": "image-refreshed", "payload": { "filename": "string", "entry": "object" } },
      "error": { "channel": "image-refresh-error", "payload": { "filename": "string", "error": "string" } }
    },
    "protocol": "single-file sharp thumbnail rebuild; same entry shape as get-images; fresh Date.now() cache-buster",
    "spawn": null,
    "implementation": "custom-handler",
    "capabilities": ["sharp", "fs", "tmp"]
  },
  {
    "id": "reset-image",
    "kind": "custom",
    "registration": "on",
    "channel": "reset-image",
    "label": "ResetImage",
    "payload": {
      "type": "object",
      "props": {
        "workingDirectory": "string",
        "outputDirectory": "string",
        "filename": "string"
      }
    },
    "return": {},
    "emit": {
      "success": { "channel": "image-reset", "payload": { "filename": "string", "success": "boolean" } },
      "error": { "channel": "image-reset-error", "payload": { "filename": "string", "error": "string" } }
    },
    "protocol": "mutates .preset.json in place + unlinkSync output file; no spawn/sharp; outputDirectory optional",
    "spawn": null,
    "implementation": "custom-handler",
    "capabilities": ["fs"]
  },
  {
    "id": "select-directory",
    "kind": "custom",
    "registration": "on",
    "channel": "select-directory",
    "label": "SelectDirectory",
    "payload": { "type": "none", "props": {} },
    "return": {},
    "emit": {
      "cancelled": { "channel": "directory-cancelled", "payload": {} },
      "success": { "channel": "directory-selected", "payload": { "path": "string", "files": "array" } },
      "error": { "channel": "directory-error", "payload": "string" }
    },
    "protocol": "dialog.showOpenDialog parented on the calling window; replies via event.sender; directory-error payload is a BARE STRING; raw directory listing",
    "spawn": null,
    "implementation": "custom-handler",
    "capabilities": ["dialog", "fs"]
  },
  {
    "id": "set-theme",
    "kind": "custom",
    "registration": "on",
    "channel": "set-theme",
    "label": "SetTheme",
    "payload": { "type": "single", "props": { "themeName": "string" } },
    "return": {},
    "emit": {},
    "protocol": "nativeTheme.themeSource = themeName === 'dark' ? 'dark' : 'light'; no emit, no spawn",
    "spawn": null,
    "implementation": "custom-handler",
    "capabilities": ["nativeTheme"]
  },
  {
    "id": "open-tool-window",
    "kind": "custom",
    "registration": "handle",
    "channel": "open-tool-window",
    "label": "OpenToolWindow",
    "payload": { "type": "single", "props": { "tool": "string", "payload": "object" } },
    "return": { "windowId": "number|null" },
    "emit": {},
    "protocol": "creates a child BrowserWindow for the tool (sized from tools.js); returns the window id, or null when the tool already has a window (singleton, no focus)",
    "spawn": null,
    "implementation": "custom-handler",
    "capabilities": ["window"]
  },
  {
    "id": "get-tool-context",
    "kind": "custom",
    "registration": "handle",
    "channel": "get-tool-context",
    "label": "GetToolContext",
    "payload": {},
    "return": { "payload": "object|null" },
    "emit": {},
    "protocol": "returns the payload the calling tool window was opened with, or null for a non-tool window",
    "spawn": null,
    "implementation": "custom-handler",
    "capabilities": ["window"]
  },
  {
    "id": "tool-result",
    "kind": "custom",
    "registration": "on",
    "channel": "tool-result",
    "label": "ToolResult",
    "payload": { "type": "single", "props": { "tool": "string", "result": "object" } },
    "return": {},
    "emit": {},
    "protocol": "fire-and-forget from a tool window; forwards {tool, result} to the owning (main) window so it can merge params and refresh",
    "spawn": null,
    "implementation": "custom-handler",
    "capabilities": ["window"]
  }
]
