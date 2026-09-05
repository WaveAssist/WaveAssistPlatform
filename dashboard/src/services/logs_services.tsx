import { callApi } from "./base_service";

export const fetchLogsApi = async (job_name: string, node_key_csv: string, nodes_array: any[]): Promise<any> => {
	if (node_key_csv === "All") {
		node_key_csv = nodes_array.map((node) => node.node_key).join(",");
	}
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		job_name: job_name,
		node_key_csv: node_key_csv,
	});
	var path = "debug/fetch_logs/";
	return callApi(path, body);
};
