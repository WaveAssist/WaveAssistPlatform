// Unit tests for the per-plan resource selection cap logic.
// No JS test runner is configured in this repo, so this uses Node's built-in
// test runner with native TypeScript type-stripping (Node >= 22):
//   node --test --experimental-strip-types src/components/resourceSelectionCap.test.mts
import { test } from "node:test";
import assert from "node:assert/strict";
import {
	remainingSlots,
	isCapReached,
	isSelectionLocked,
	fitUnderCap,
	capHint,
} from "./resourceSelectionCap.ts";

// ── remainingSlots ────────────────────────────────────────────────────────────
test("remainingSlots counts down toward the cap", () => {
	assert.equal(remainingSlots(0, 5), 5);
	assert.equal(remainingSlots(3, 5), 2);
	assert.equal(remainingSlots(5, 5), 0);
});

test("remainingSlots never goes negative for an over-cap selection", () => {
	// e.g. a Pro account with 8 repos downgraded to the trial cap of 5.
	assert.equal(remainingSlots(8, 5), 0);
});

test("remainingSlots is Infinity when uncapped (undefined / 0 / negative)", () => {
	assert.equal(remainingSlots(100), Infinity);
	assert.equal(remainingSlots(100, 0), Infinity);
	assert.equal(remainingSlots(100, -1), Infinity);
});

// ── isCapReached ──────────────────────────────────────────────────────────────
test("isCapReached is true only at or past the cap", () => {
	assert.equal(isCapReached(4, 5), false);
	assert.equal(isCapReached(5, 5), true);
	assert.equal(isCapReached(6, 5), true);
});

test("isCapReached is never true when uncapped", () => {
	assert.equal(isCapReached(999), false);
	assert.equal(isCapReached(999, 0), false);
});

// ── isSelectionLocked ─────────────────────────────────────────────────────────
test("unselected rows lock once the cap is reached", () => {
	assert.equal(isSelectionLocked(false, 5, 5), true);
	assert.equal(isSelectionLocked(false, 4, 5), false);
});

test("already-selected rows never lock (can always be removed to free a slot)", () => {
	assert.equal(isSelectionLocked(true, 5, 5), false);
	assert.equal(isSelectionLocked(true, 8, 5), false);
});

test("no row locks when uncapped, even with a huge selection", () => {
	assert.equal(isSelectionLocked(false, 999), false);
	assert.equal(isSelectionLocked(false, 999, 0), false);
});

// ── fitUnderCap ───────────────────────────────────────────────────────────────
test("fitUnderCap adds candidates only up to the remaining slots, in order", () => {
	const selected = new Set(["a", "b"]); // 2 of 5 used -> room for 3 more
	const result = fitUnderCap(selected, ["c", "d", "e", "f", "g"], 5);
	assert.deepEqual(result, ["c", "d", "e"]);
});

test("fitUnderCap skips already-selected candidates before counting room", () => {
	const selected = new Set(["a", "b"]); // room for 3
	// a and b are already in; only c, d, e, f are new -> take first 3 of those.
	const result = fitUnderCap(selected, ["a", "b", "c", "d", "e", "f"], 5);
	assert.deepEqual(result, ["c", "d", "e"]);
});

test("fitUnderCap returns nothing when the cap is already full", () => {
	const selected = new Set(["a", "b", "c", "d", "e"]);
	assert.deepEqual(fitUnderCap(selected, ["f", "g"], 5), []);
});

test("fitUnderCap adds every new candidate when uncapped", () => {
	const selected = new Set(["a"]);
	assert.deepEqual(fitUnderCap(selected, ["a", "b", "c", "d"]), ["b", "c", "d"]);
});

// ── capHint ───────────────────────────────────────────────────────────────────
test("capHint shows remaining room below the cap", () => {
	assert.equal(capHint(3, 5), "3 of 5 selected. Add up to 2 more.");
	assert.equal(capHint(0, 5), "0 of 5 selected. Add up to 5 more.");
});

test("capHint switches to the limit-reached message at the cap", () => {
	assert.equal(
		capHint(5, 5),
		"Plan limit reached (5 of 5 selected). Remove one to choose a different resource."
	);
});

test("capHint reports the real count when a selection is over the cap (e.g. after a downgrade)", () => {
	assert.equal(
		capHint(8, 5),
		"Plan limit reached (8 of 5 selected). Remove one to choose a different resource."
	);
});

test("capHint is empty when uncapped (renders nothing)", () => {
	assert.equal(capHint(3), "");
	assert.equal(capHint(3, 0), "");
});
