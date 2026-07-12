// Pure auto-selection logic for the resource picker, kept React-free so it can be
// unit-tested in isolation (see resourceAutoSelect.test.mts).

export interface AutoSelectResource {
	id: string;
	archived?: boolean;
}

// On first connect (no saved selection): <= this -> select all; more -> preselect the
// N most recently pushed, non-archived resources.
export const AUTO_SELECT_THRESHOLD = 15;

/**
 * Compute the auto-preselection applied when a provider is connected and the user has
 * no saved selection yet. Returns the ids to select plus a banner notice.
 *
 * Contract:
 *  - hasSavedSelection -> never clobber: select nothing here (caller keeps the saved set).
 *  - no resources -> select nothing.
 *  - <= AUTO_SELECT_THRESHOLD -> select all.
 *  - > AUTO_SELECT_THRESHOLD -> the first N non-archived (resources arrive most-recent-first).
 *  - limit (optional) -> hard cap on how many are auto-selected, applied AFTER the above.
 *    Used for GitZoid's per-plan repo cap (trial = 5, Pro = 50) so first-connect can't
 *    auto-select past the cap and trigger a save error. Omit / <=0 means no cap (WaveAssist).
 */
export function computeAutoSelection<T extends AutoSelectResource>(
	resources: T[],
	hasSavedSelection: boolean,
	limit?: number
): { ids: string[]; notice: string } {
	if (hasSavedSelection) {
		return { ids: [], notice: "" };
	}
	if (resources.length === 0) {
		return { ids: [], notice: "" };
	}

	const total = resources.length;
	// Base preselection: small sets take all; larger sets take the most-recent, non-archived
	// (resources arrive most-recent-first from the API).
	const base =
		total <= AUTO_SELECT_THRESHOLD
			? resources.slice()
			: resources.filter((r) => !r.archived).slice(0, AUTO_SELECT_THRESHOLD);

	// Cap to the account's connect limit when one applies. Auto-selecting the first `limit`
	// keeps the connect-and-done UX while staying under the cap; the user can swap which ones.
	if (typeof limit === "number" && limit > 0 && base.length > limit) {
		const capped = base.slice(0, limit);
		return {
			ids: capped.map((r) => r.id),
			notice: `Selected ${capped.length} of ${total} repos — your plan covers ${limit}. Swap any before saving.`,
		};
	}

	return {
		ids: base.map((r) => r.id),
		notice:
			total <= AUTO_SELECT_THRESHOLD
				? `Selected all ${total} repos — add or remove anytime.`
				: `Selected your ${base.length} most active repos — add more anytime.`,
	};
}
