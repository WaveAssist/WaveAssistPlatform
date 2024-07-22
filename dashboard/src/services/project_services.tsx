import { callApi } from "./base_service";

export const fetchNodesApi = async (): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
	});
	var path = "manage/fetch_nodes/";
	return callApi(path, body);
};
