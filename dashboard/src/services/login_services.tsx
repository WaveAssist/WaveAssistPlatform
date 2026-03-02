import { auth } from "../utils/firebase";
import { callApi } from "./base_service";

export const refreshUserProfile = async (): Promise<void> => {
	try {
		const currentUser = auth.currentUser;
		if (!currentUser) return;

		const freshToken = await currentUser.getIdToken();
		const data = await loginAPI(freshToken);

		// Skip redirect flows — only sync profile data
		if (!data || data.action === "PERFORM_GET_STARTED") return;

		if (data.user_data) {
			localStorage.setItem("user_data", JSON.stringify(data.user_data));
			localStorage.setItem("is_premium", data.user_data.is_premium ? "true" : "false");
			if (data.user_data.plan_name) {
				localStorage.setItem("plan_name", data.user_data.plan_name);
			}
		}
		if (data.project_array) {
			localStorage.setItem("projects_array", JSON.stringify(data.project_array));
		}
	} catch {
		// Silent fail — never interrupt the user experience
	}
};

export const loginAPI = async (firebase_token: any, session_id?: any): Promise<any> => {
	var path = "login/";
	const body = new URLSearchParams({ firebase_token: firebase_token });
	if (session_id) body.append("session_id", session_id);
	return callApi(path, body);
};

export const getStartedAPI = async (firebase_token: any, is_test: boolean = false, session_id?: any): Promise<any> => {
	var path = "manage/get_started/";
	const body = new URLSearchParams({ firebase_token: firebase_token, is_test: is_test ? "1" : "0" });
	if (session_id) body.append("session_id", session_id);
	return callApi(path, body);
};
