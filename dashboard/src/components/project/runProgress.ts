// Live-progress ring gating for the Runs view.
//
// The runs list keeps a `runProgress` map (run_id -> { progress, remaining }) that
// is only ever ADDED to while a run is processing; it is never pruned when a run
// finishes. So a run that has completed can still have a stale entry in that map.
//
// The rule these helpers enforce: the live progress ring must render ONLY for a run
// that is still processing. Existence of a `runProgress` entry alone must NOT gate
// the ring, or a finished run keeps showing its last (capped) percentage until the
// page is refreshed and the map resets.

// A run is "processing" while the backend reports it as started or running.
export const isRunProcessing = (status?: string): boolean =>
	status === "STARTED" || status === "RUNNING";

// Show the live ring only when the run is still processing AND we have a progress
// entry to draw. Both conditions are required — see the note above.
export const shouldShowLiveProgress = (status: string | undefined, hasProgressEntry: boolean): boolean =>
	isRunProcessing(status) && hasProgressEntry;
