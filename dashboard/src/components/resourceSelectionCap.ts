// Pure enforcement logic for a per-plan resource selection cap (GitZoid trial = 5 repos), kept
// React-free so the selection math can be unit-tested in isolation (see resourceSelectionCap.test.mts).
//
// A cap that is undefined, non-numeric, or <= 0 means "no cap" — WaveAssist and every provider that
// isn't capped keep their previous unlimited behavior. All helpers are total (no throws) and treat a
// pre-existing over-cap selection (e.g. an account downgraded from Pro) gracefully: nothing is
// auto-removed, but no further additions are allowed until the user is back under the cap.

const capActive = (cap?: number): cap is number =>
	typeof cap === "number" && Number.isFinite(cap) && cap > 0;

/**
 * Slots left before the cap is reached. `Infinity` when uncapped; never negative even if the current
 * selection already exceeds the cap.
 */
export function remainingSlots(selectedCount: number, cap?: number): number {
	if (!capActive(cap)) return Infinity;
	return Math.max(0, cap - selectedCount);
}

/** Whether the cap is met or exceeded. Uncapped selections are never "reached". */
export function isCapReached(selectedCount: number, cap?: number): boolean {
	return remainingSlots(selectedCount, cap) === 0;
}

/**
 * Whether a specific row's Select control should be locked. Only *unselected* rows lock, and only
 * once the cap is reached — an already-selected row always stays toggleable so the user can deselect
 * it to free a slot.
 */
export function isSelectionLocked(isSelected: boolean, selectedCount: number, cap?: number): boolean {
	if (isSelected) return false;
	return isCapReached(selectedCount, cap);
}

/**
 * Given the current selection and an ordered list of candidate ids (e.g. a "Select all" click),
 * return the ids that can actually be added under the cap, in order. Already-selected candidates are
 * skipped. Uncapped returns every not-yet-selected candidate.
 */
export function fitUnderCap(selectedIds: Set<string>, candidateIds: string[], cap?: number): string[] {
	const toAdd = candidateIds.filter((id) => !selectedIds.has(id));
	if (!capActive(cap)) return toAdd;
	return toAdd.slice(0, remainingSlots(selectedIds.size, cap));
}

/**
 * The live cap indicator shown above the list. Empty string when uncapped, so callers can render it
 * unconditionally.
 */
export function capHint(selectedCount: number, cap?: number): string {
	if (!capActive(cap)) return "";
	const remaining = remainingSlots(selectedCount, cap);
	if (remaining > 0) {
		return `${selectedCount} of ${cap} selected. Add up to ${remaining} more.`;
	}
	// selectedCount (not cap) so an over-cap selection reads honestly, e.g. "8 of 5" after a downgrade.
	return `Plan limit reached (${selectedCount} of ${cap} selected). Remove one to choose a different resource.`;
}
