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

export const createPaymentOrder = async (provider: string, amount: string, currency: string, uid: string, creditsInUsd: string): Promise<any> => {
	const body = new FormData();
	body.append("provider", provider);
	body.append("amount", amount);
	body.append("currency", currency);
	body.append("uid", uid);
	body.append("credits_in_usd", creditsInUsd);

	const response = await fetch("https://api.waveassist.io/payment/create_payment_order/", {
		method: "POST",
		body: body,
	});

	if (!response.ok) {
		throw new Error("Failed to create payment order");
	}

	return response.json();
};

export const verifyPayment = async (
	provider: string,
	amount: string,
	currency: string,
	uid: string,
	providerPaymentId: string,
	signature: string,
	razorpayPaymentId: string,
	paypalPayerId: string
): Promise<any> => {
	const body = new FormData();
	body.append("provider", provider);
	body.append("amount", amount);
	body.append("currency", currency);
	body.append("uid", uid);
	body.append("provider_payment_id", providerPaymentId);
	body.append("signature", signature);
	body.append("razorpay_payment_id", razorpayPaymentId);
	body.append("paypal_payer_id", paypalPayerId);

	const response = await fetch("https://api.waveassist.io/payment/verify_payment/", {
		method: "POST",
		body: body,
	});

	if (!response.ok) {
		throw new Error("Failed to verify payment");
	}

	return response.json();
};
