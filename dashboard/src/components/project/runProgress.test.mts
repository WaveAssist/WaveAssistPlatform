// Unit tests for the live-progress ring gating in the Runs view.
// No JS test runner is configured in this repo, so this uses Node's built-in
// test runner with native TypeScript type-stripping (Node >= 22):
//   node --test --experimental-strip-types src/components/project/runProgress.test.mts
import { test } from "node:test";
import assert from "node:assert/strict";
import { isRunProcessing, shouldShowLiveProgress } from "./runProgress.ts";

// ── isRunProcessing ───────────────────────────────────────────────────────────
test("isRunProcessing is true only for started/running runs", () => {
	assert.equal(isRunProcessing("STARTED"), true);
	assert.equal(isRunProcessing("RUNNING"), true);
	assert.equal(isRunProcessing("SUCCESS"), false);
	assert.equal(isRunProcessing("FAILED"), false);
	assert.equal(isRunProcessing(undefined), false);
});

// ── shouldShowLiveProgress ─────────────────────────────────────────────────────
test("live ring shows for a processing run that has a progress entry", () => {
	assert.equal(shouldShowLiveProgress("RUNNING", true), true);
	assert.equal(shouldShowLiveProgress("STARTED", true), true);
});

test("live ring is hidden for a finished run even with a stale progress entry", () => {
	// This is the bug: a completed run kept its progress entry (map is never pruned)
	// and the card showed the frozen percentage until refresh.
	assert.equal(shouldShowLiveProgress("SUCCESS", true), false);
	assert.equal(shouldShowLiveProgress("FAILED", true), false);
});

test("live ring is hidden for a processing run with no progress entry yet", () => {
	assert.equal(shouldShowLiveProgress("RUNNING", false), false);
});
