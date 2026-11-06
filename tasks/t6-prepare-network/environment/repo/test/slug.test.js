const test = require('node:test');
const assert = require('node:assert');
const { slugify, truncateSlug } = require('../src');

test('lowercases and joins words', () => {
  assert.strictEqual(slugify('Hello World'), 'hello-world');
});

test('collapses runs of separators', () => {
  assert.strictEqual(slugify('Hello,   World!!'), 'hello-world');
});

test('trims leading and trailing separators', () => {
  assert.strictEqual(slugify('  --Hello-- '), 'hello');
});

test('truncates without trailing hyphen', () => {
  assert.strictEqual(truncateSlug('hello-world', 6), 'hello');
});
