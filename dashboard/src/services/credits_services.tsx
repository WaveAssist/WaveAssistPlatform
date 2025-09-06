import { callApi } from "./base_service";

export const fetchCreditsApi = async (): Promise<any> => {
    const uid = localStorage.getItem("uid") || "";
    if (!uid) {
        throw new Error("User ID not found");
    }
    
    const path = `fetch_openrouter_credits/${uid}/`;
    return callApi(path, new URLSearchParams());
};
