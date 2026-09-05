import { callApi } from "./base_service";

export const fetchResourcesApi = async (providerName: string): Promise<any> => {
	const uid = localStorage.getItem("uid");
	const projectKey = localStorage.getItem("selected_project_key");

	if (!uid || !projectKey) {
		throw new Error("Missing user ID or project key");
	}

	const body = new URLSearchParams({
		uid: uid,
		project_key: projectKey,
		provider_name: providerName,
	});

	return await callApi("providers/fetch_resources/", body);
};
