import axios from "axios";

const BASE_URL = import.meta.env.VITE_DASHBOARD_BASE_URL || "https://api.waveassist.io";
// const BASE_URL = import.meta.env.VITE_DASHBOARD_BASE_URL || "http://localhost:8000";

export const callApi = async (path: string, body: URLSearchParams): Promise<any> => {
	const url = `${BASE_URL}/${path}`;
	const headers = { "Content-Type": "application/x-www-form-urlencoded" };
	try {
		const response = await axios.post(url, body, { headers });
		const responseDict = response.data;
		if (responseDict.success === "1") {
			if (responseDict && responseDict.data) {
				return responseDict.data;
			} else {
				throw new Error("Invalid response structure");
			}
		} else {
			var error_message = responseDict.message;
			throw new Error(error_message);
		}
	} catch (error) {
		console.error(error);
		throw error;
	}
};

export const callApiRaw = async (path: string, body: URLSearchParams): Promise<any> => {
	const url = `${BASE_URL}/${path}`;
	const headers = { "Content-Type": "application/x-www-form-urlencoded" };
	try {
		const response = await axios.post(url, body, { headers });
		return response;
	} catch (error) {
		console.error(error);
		throw error;
	}
};
