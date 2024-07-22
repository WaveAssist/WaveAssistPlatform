import { callApi } from "./base_service";

export const fetchAllProjectsAPI = async (): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
	});
	var path = "manage/fetch_all_projects/";
	return callApi(path, body);
};

export const createProjectAPI = async (projectName: string, projectKey: string): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: projectKey,
		project_name: projectName,
	});
	var path = "manage/create_project/";
	return callApi(path, body);
};

export const deleteProjectApi = async (projectKey: string): Promise<any> => {
	var path = "manage/delete_project/";
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: projectKey,
	});
	return callApi(path, body);
};
