// fetchEnvironmentsApi, createEnvironmentApi, updateEnvironmentApi, deleteEnvironmentApi
import { callApi } from "./base_service";

// fetchEnvironmentsApi,
export const fetchEnvironmentsApi = async (): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
	});
	var path = "manage/fetch_environments/";
	return callApi(path, body);
};

// createEnvironmentApi,
export const createEnvironmentApi = async (environmentData: any): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		name: environmentData.name,
		is_enabled: environmentData.is_enabled ? "1" : "0",
	});
	var path = "manage/create_data_run/";
	return callApi(path, body);
};

// updateEnvironmentApi
export const updateEnvironmentApi = async (environmentKey: string, environmentData: any): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		data_run_key: environmentKey,
		name: environmentData.name,
		is_enabled: environmentData.is_enabled ? "1" : "0",
	});
	var path = "manage/update_data_run/";
	return callApi(path, body);
};

// deleteEnvironmentApi
export const deleteEnvironmentApi = async (environmentKey: string): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		data_run_key: environmentKey,
	});
	var path = "manage/delete_data_run/";
	return callApi(path, body);
};
