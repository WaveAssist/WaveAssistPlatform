// Unit tests for the auto-select-count logic.
// No JS test runner is configured in this repo, so this uses Node's built-in
// test runner with native TypeScript type-stripping (Node >= 22):
//   node --test --experimental-strip-types src/components/resourceAutoSelect.test.mts
import { test } from "node:test";
import assert from "node:assert/strict";
import { computeAutoSelection, AUTO_SELECT_THRESHOLD } from "./resourceAutoSelect.ts";

const makeRepos = (n: number, archivedIds: Set<string> = new Set()) =>
	Array.from({ length: n }, (_, i) => {
		const id = `repo-${i}`;
		return { id, archived: archivedIds.has(id) };
	});

test("<= threshold with no saved selection -> select all + 'all' banner", () => {
	const repos = makeRepos(10);
	const { ids, notice } = computeAutoSelection(repos, false);
	assert.equal(ids.length, 10);
	assert.deepEqual(ids, repos.map((r) => r.id));
	assert.equal(notice, "Selected all 10 repos — add or remove anytime.");
});

test("exactly threshold -> still select all", () => {
	const { ids } = computeAutoSelection(makeRepos(AUTO_SELECT_THRESHOLD), false);
	assert.equal(ids.length, AUTO_SELECT_THRESHOLD);
});

test("> threshold -> preselect exactly threshold, excluding archived", () => {
	// 40 repos, mark some of the top entries archived so they are skipped.
	const archived = new Set(["repo-0", "repo-2", "repo-5"]);
	const repos = makeRepos(40, archived);
	const { ids, notice } = computeAutoSelection(repos, false);
	assert.equal(ids.length, AUTO_SELECT_THRESHOLD);
	for (const id of ids) {
		assert.ok(!archived.has(id), `archived repo ${id} should not be selected`);
	}
	assert.equal(notice, "Selected your 15 most active repos — add more anytime.");
});

test("> threshold preserves most-recent-first order (no archived)", () => {
	const repos = makeRepos(30);
	const { ids } = computeAutoSelection(repos, false);
	// resources arrive sorted; the first 15 ids should be the first 15 repos.
	assert.deepEqual(ids, repos.slice(0, AUTO_SELECT_THRESHOLD).map((r) => r.id));
});

test("saved selection is respected -> auto-select returns nothing, no banner", () => {
	const { ids, notice } = computeAutoSelection(makeRepos(40), true);
	assert.equal(ids.length, 0);
	assert.equal(notice, "");
});

test("no resources -> nothing selected, no banner", () => {
	const { ids, notice } = computeAutoSelection([], false);
	assert.equal(ids.length, 0);
	assert.equal(notice, "");
});

test("> threshold where fewer than threshold are non-archived -> selects all active", () => {
	// 20 repos but only 12 active -> select those 12.
	const archived = new Set(Array.from({ length: 8 }, (_, i) => `repo-${i + 12}`));
	const repos = makeRepos(20, archived);
	const { ids } = computeAutoSelection(repos, false);
	assert.equal(ids.length, 12);
});

// ── GitZoid per-plan cap (limit argument) ─────────────────────────────────────
test("limit caps auto-selection below the base set (trial = 5)", () => {
	// 8 repos would normally all be selected (<= threshold); the trial cap of 5 trims it.
	const repos = makeRepos(8);
	const { ids, notice } = computeAutoSelection(repos, false, 5);
	assert.equal(ids.length, 5);
	assert.deepEqual(ids, repos.slice(0, 5).map((r) => r.id));
	assert.equal(notice, "Selected 5 of 8 repos — your plan covers 5. Swap any before saving.");
});

test("limit caps the top-N branch too (> threshold, trial = 5)", () => {
	const { ids } = computeAutoSelection(makeRepos(40), false, 5);
	assert.equal(ids.length, 5);
});

test("limit >= base set is a no-op (Pro = 50 with few repos)", () => {
	const repos = makeRepos(8);
	const { ids, notice } = computeAutoSelection(repos, false, 50);
	assert.equal(ids.length, 8);
	assert.equal(notice, "Selected all 8 repos — add or remove anytime.");
});

test("no limit (WaveAssist) -> unchanged behavior", () => {
	const repos = makeRepos(8);
	const { ids } = computeAutoSelection(repos, false);
	assert.equal(ids.length, 8);
});

test("limit is ignored when a saved selection exists", () => {
	const { ids, notice } = computeAutoSelection(makeRepos(40), true, 5);
	assert.equal(ids.length, 0);
	assert.equal(notice, "");
});
