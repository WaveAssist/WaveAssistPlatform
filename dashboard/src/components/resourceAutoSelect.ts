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
 */
export function computeAutoSelection<T extends AutoSelectResource>(
	resources: T[],
	hasSavedSelection: boolean
): { ids: string[]; notice: string } {
	if (hasSavedSelection) {
		return { ids: [], notice: "" };
	}
	if (resources.length === 0) {
		return { ids: [], notice: "" };
	}
	if (resources.length <= AUTO_SELECT_THRESHOLD) {
		return {
			ids: resources.map((r) => r.id),
			notice: `Selected all ${resources.length} repos — add or remove anytime.`,
		};
	}
	// resources already arrive sorted most-recent-first from the API; exclude archived.
	const top = resources.filter((r) => !r.archived).slice(0, AUTO_SELECT_THRESHOLD);
	return {
		ids: top.map((r) => r.id),
		notice: `Selected your ${top.length} most active repos — add more anytime.`,
	};
}
