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
 *    For GitZoid we auto-select a conservative default (trial = 3) that sits BELOW the plan's
 *    hard cap, so trial credits stretch across more digest runs and the user adds their own key
 *    repos up to the cap (a one-click add, not a swap). Omit / <=0 means no cap (WaveAssist).
 *  - planCap (optional) -> the plan's real max selectable (trial = 5, Pro = 50). Used only to
 *    keep the notice honest ("your plan covers 5") when `limit` auto-selects fewer than the cap.
 *    Defaults to `limit` when omitted (i.e. auto-select fills the cap exactly).
 */
export function computeAutoSelection<T extends AutoSelectResource>(
	resources: T[],
	hasSavedSelection: boolean,
	limit?: number,
	planCap?: number
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

	// Cap the auto-selection to `limit` when one applies. Auto-selecting the first `limit` keeps the
	// connect-and-done UX; when the plan allows more (planCap > limit) we say so and invite the user
	// to add, rather than telling them to swap.
	if (typeof limit === "number" && limit > 0 && base.length > limit) {
		const capped = base.slice(0, limit);
		const cap = typeof planCap === "number" && planCap > limit ? planCap : limit;
		return {
			ids: capped.map((r) => r.id),
			notice:
				cap > capped.length
					? `Selected your ${capped.length} most active repos. Your plan covers ${cap}, add more anytime.`
					: `Selected your ${capped.length} most active of ${total} repos. You can include up to ${cap}, swap any before saving.`,
		};
	}

	return {
		ids: base.map((r) => r.id),
		notice:
			total <= AUTO_SELECT_THRESHOLD
				? `Selected all ${total} repos. Add or remove anytime.`
				: `Selected your ${base.length} most active repos. Add more anytime.`,
	};
}
