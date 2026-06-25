const test = require('node:test')
const assert = require('node:assert/strict')

const {
  getVersionChannel,
  normalizeVersion,
  parseRecallData,
  isChineseLocale,
  shouldCheckByHour
} = require('../version')

test('getVersionChannel classifies suffixes', () => {
  assert.equal(getVersionChannel('v1.4.3'), 'stable')
  assert.equal(getVersionChannel('v1.4.3-rc.6'), 'rc')
  assert.equal(getVersionChannel('v1.4.3-beta.1'), 'beta')
  assert.equal(getVersionChannel('v1.4.3-alpha.2'), 'alpha')
  assert.equal(getVersionChannel('1.4.3-RC.6'), 'rc') // case-insensitive
})

test('getVersionChannel defaults to stable for empty/falsy', () => {
  assert.equal(getVersionChannel(''), 'stable')
  assert.equal(getVersionChannel(undefined), 'stable')
  assert.equal(getVersionChannel(null), 'stable')
})

test('normalizeVersion ensures a leading v', () => {
  assert.equal(normalizeVersion('1.4.3'), 'v1.4.3')
  assert.equal(normalizeVersion('v1.4.3'), 'v1.4.3')
  assert.equal(normalizeVersion(''), '')
  assert.equal(normalizeVersion(undefined), undefined)
})

test('parseRecallData recalls only when version matches', () => {
  assert.deepEqual(
    parseRecallData('recall:v1.4.3', 'v1.4.3'),
    { recalled: true, version: 'v1.4.3' }
  )
  assert.deepEqual(
    parseRecallData('recall:v1.4.2', 'v1.4.3'),
    { recalled: false }
  )
})

test('parseRecallData treats timestamps and junk as not recalled', () => {
  assert.deepEqual(parseRecallData('1718000000000', 'v1.4.3'), { recalled: false })
  assert.deepEqual(parseRecallData('', 'v1.4.3'), { recalled: false })
  assert.deepEqual(parseRecallData(null, 'v1.4.3'), { recalled: false })
})

test('parseRecallData tolerates surrounding whitespace', () => {
  assert.deepEqual(
    parseRecallData('  recall:v1.4.3\n', 'v1.4.3'),
    { recalled: true, version: 'v1.4.3' }
  )
})

test('isChineseLocale recognizes the Simplified variants', () => {
  for (const l of ['zh_cn', 'zh-cn', 'zh-hans', 'zh_hans', 'ZH-CN']) {
    assert.equal(isChineseLocale(l), true, l)
  }
  for (const l of ['en', 'en-US', 'zh-tw', 'zh_hant', '', undefined]) {
    assert.equal(isChineseLocale(l), false, String(l))
  }
})

test('shouldCheckByHour checks once per wall-clock hour', () => {
  const HOUR = 60 * 60 * 1000
  // Never checked → always check
  assert.equal(shouldCheckByHour(0, 5 * HOUR), true)
  // Same hour bucket → skip
  assert.equal(shouldCheckByHour(5 * HOUR + 100, 5 * HOUR + 200), false)
  // Next hour bucket → check
  assert.equal(shouldCheckByHour(5 * HOUR + 100, 6 * HOUR), true)
})
