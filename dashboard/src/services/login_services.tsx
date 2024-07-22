import { callApi } from "./base_service";

export const loginAPI = async (username: string, password: string): Promise<any> => {
	var path = "login/";
	const body = new URLSearchParams({ username: username, password: password });
	return callApi(path, body);
};
