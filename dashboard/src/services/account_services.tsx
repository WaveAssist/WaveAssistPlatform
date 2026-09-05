import { callApi } from "./base_service";

const uid = () => localStorage.getItem("uid") || "";

/** Per-run LLM usage for a project (WaveAssist runs pages). Returns { runs: [...] }.
 *  Empty until the instrumented SDK (>=0.8.11) records ledger rows. */
export const fetchRunUsage = async (projectKey: string, runId?: string): Promise<any> => {
	const body = new URLSearchParams({ uid: uid(), project_key: projectKey });
	if (runId) body.append("run_id", runId);
	return callApi("account/run_usage/", body);
};

/** Rotate the account's MCP bearer token. Identity (uid) is unaffected. */
export const regenerateMcpToken = async (): Promise<any> => {
	const body = new URLSearchParams({ uid: uid() });
	return callApi("account/regenerate_mcp_token/", body);
};
