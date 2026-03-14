import { callApi, BASE_URL } from "./base_service";

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
		should_create_nodes: "1",
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

export const createCheckoutSession = async (
	uid: string,
	useCase: "credits" | "subscription",
	amount: string,
	creditsInUsd: string,
	planName?: string
): Promise<any> => {
	const body = new FormData();
	body.append("uid", uid);
	body.append("use_case", useCase);
	body.append("amount", amount);
	body.append("credits_in_usd", creditsInUsd);
	if (planName) body.append("plan_name", planName);

	const response = await fetch(`${BASE_URL}/payment/create_checkout/`, {
		method: "POST",
		body: body,
	});

	if (!response.ok) {
		throw new Error("Failed to create payment order");
	}

	return response.json();
};

export const fetchBillingOverview = async (uid: string): Promise<any> => {
	const body = new URLSearchParams({ uid });
	return callApi("payment/billing_overview/", body);
};

export const createBillingPortalSession = async (uid: string): Promise<any> => {
	const body = new URLSearchParams({ uid });
	return callApi("payment/create_portal_session/", body);
};
