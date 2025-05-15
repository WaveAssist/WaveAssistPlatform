import { callApi } from "./base_service";

export const loginAPI = async (firebase_token: any): Promise<any> => {
	var path = "login/";

	const body = new URLSearchParams({ firebase_token: firebase_token });
	return callApi(path, body);
};

export const getStartedAPI = async (firebase_token: any, is_test: boolean = false): Promise<any> => {
	var path = "manage/get_started/";
	const body = new URLSearchParams({ firebase_token: firebase_token, is_test: is_test ? "1" : "0" });
	return callApi(path, body);
};
