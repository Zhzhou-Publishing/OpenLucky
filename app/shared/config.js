// Compile-time tunables for the Electron app.
//
// These are read by the main process only; the renderer reacts to events main
// emits, so nothing here needs to cross IPC (unless a future UI wants to
// display the raw ratio). Change the constant and rebuild to tune.

// 先行使用 (early use): the ready ratio at which the prepare job emits
// `working-directory-partial-ready` and lets the user into the gallery while
// the remaining images lazy-load in the background. `OPENLUCKY_EARLY_USE_RATIO`
// overrides it in dev without a rebuild.
const EARLY_USE_READY_RATIO = parseFloat(process.env.OPENLUCKY_EARLY_USE_RATIO) || (1 / 3)

module.exports = { EARLY_USE_READY_RATIO }
