// Shared IPC engine — registers ipcMain handlers from the backend contract.
//
// Two entry points:
//   registerEntry(id, runtime)  — for 'engine-driver' entries. The engine builds
//                                 the handler from the contract metadata + a
//                                 small runtime config (arg mapping, payload
//                                 builders, finalize hooks). Handles spawn-json
//                                 and spawn-stream kinds.
//   registerHandler(id, fn)     — for 'custom-handler' entries. The delegator
//                                 keeps its handler body; the engine only
//                                 validates the entry and performs the
//                                 ipcMain[registration] call.
//
// The engine requires electron / child_process / shared modules itself so the
// test harness's Module._load interceptors mock them exactly as they do the
// current per-file handlers.
const CONTRACT = require('../shared/backend-contract')
const { ipcMain } = require('electron')
const { spawn } = require('child_process')
const { buildOpenLuckyCommand } = require('../shared/utils')
const { createLogger } = require('../shared/logger')

function getEntry(id) {
  const e = CONTRACT.find((x) => x.id === id)
  if (!e) throw new Error(`backend-contract: unknown id "${id}"`)
  return e
}

function registerEntry(id, runtime) {
  const e = getEntry(id)
  if (e.implementation !== 'engine-driver') {
    throw new Error(`backend-contract: "${id}" is ${e.implementation}; use registerHandler`)
  }
  const fn = e.kind === 'spawn-json' ? spawnJsonHandler(e, runtime) : spawnStreamHandler(e, runtime)
  ipcMain[e.registration](e.channel, fn)
  return fn
}

function registerHandler(id, fn) {
  const e = getEntry(id)
  if (e.implementation !== 'custom-handler') {
    throw new Error(`backend-contract: "${id}" is ${e.implementation}; use registerEntry`)
  }
  if (typeof fn !== 'function') throw new Error(`backend-contract: "${id}" needs a handler fn`)
  ipcMain[e.registration](e.channel, fn)
  return fn
}

// ── spawn-json driver ─────────────────────────────────────────────────────────
// Spawns the CLI, collects stdout/stderr, resolves JSON.parse(stdout) on exit 0,
// rejects otherwise. Error message wording is provided by the delegator via
// runtime.errors so it can stay byte-identical to the original handler.

function spawnJsonHandler(e, rt) {
  return function (_event, payload) {
    return new Promise((resolve, reject) => {
      const { command, prefixArgs, spawnOptions } = buildOpenLuckyCommand()
      const args = [...prefixArgs, ...rt.buildArgs(payload)]
      const child = spawn(command, args, {
        ...spawnOptions,
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true
      })

      let stdout = ''
      let stderr = ''
      child.stdout.on('data', (data) => { stdout += data.toString() })
      child.stderr.on('data', (data) => { stderr += data.toString() })

      const msgs = rt.errors
      child.on('error', (err) => {
        reject(new Error(msgs.spawn + err.message))
      })

      child.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(stderr.trim() || msgs.exit + code))
          return
        }
        try {
          resolve(JSON.parse(stdout))
        } catch (parseErr) {
          reject(new Error(msgs.parse + parseErr.message))
        }
      })
    })
  }
}

// ── spawn-stream driver ───────────────────────────────────────────────────────
// Two modes selected by e.finalize:
//   terminal mode (apply-*): started -> progress* -> success | error
//   finalize mode (check-openlucky / get-presets): close/error delegate to
//     rt.finalize / rt.onSpawnError / rt.onError, which decide the events.

function spawnStreamHandler(e, rt) {
  return async function (event, ...payload) {
    const send = (ch, p) => { if (!event.sender.isDestroyed()) event.sender.send(ch, p) }
    const arg0 = payload[0]
    try {
      const { command, prefixArgs, spawnOptions } = buildOpenLuckyCommand()
      const args = [...prefixArgs, ...rt.buildArgs(arg0)]
      createLogger(e.label).info(`[openlucky] Executing: ${command} ${args.join(' ')}`)

      if (e.emit.started) {
        send(e.emit.started.channel, { message: rt.startedMessage ?? 'Processing started' })
      }

      const child = spawn(command, args, {
        ...spawnOptions,
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true
      })

      let output = ''
      let errorOutput = ''
      child.stdout.on('data', (data) => {
        output += data.toString()
        if (e.emit.progress) send(e.emit.progress.channel, { data: data.toString() })
      })
      child.stderr.on('data', (data) => { errorOutput += data.toString() })

      child.on('close', (code) => {
        if (event.sender.isDestroyed()) return
        if (e.finalize) {
          rt.finalize({ code, stdout: output, stderr: errorOutput, send })
          return
        }
        if (code === 0) {
          if (e.emit.success) {
            send(e.emit.success.channel, rt.successPayload
              ? rt.successPayload(arg0)
              : { message: rt.successMessage ?? 'Success' })
          }
        } else if (e.emit.error) {
          send(e.emit.error.channel, { message: `Process exited with code ${code}`, error: errorOutput })
        }
      })

      child.on('error', (err) => {
        if (event.sender.isDestroyed()) return
        if (e.finalize) {
          if (rt.onSpawnError) rt.onSpawnError({ error: err, send })
          return
        }
        if (e.emit.error) {
          send(e.emit.error.channel, { message: 'Failed to start process', error: err.message })
        }
      })
    } catch (error) {
      createLogger(e.label).error(`Error handling ${e.id}:`, error)
      if (event.sender.isDestroyed()) return
      if (e.finalize) {
        if (rt.onError) rt.onError({ error, send })
        return
      }
      if (e.emit.error) {
        event.sender.send(e.emit.error.channel, { message: rt.errorMessage ?? 'Error', error: error.message })
      }
    }
  }
}

module.exports = { registerEntry, registerHandler, CONTRACT }
