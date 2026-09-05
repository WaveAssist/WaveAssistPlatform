import { callApi } from "./base_service";

export const fetchEnvironmentsApi = async (): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
	});
	var path = "manage/fetch_environments/";
	return callApi(path, body);
};

export const deployProjectApi = async (versionCode: string): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		version: versionCode,
		data_run_key: localStorage.getItem("selected_env_key") || "",
	});
	var path = "deploy/deploy_project/";
	return callApi(path, body);
};
