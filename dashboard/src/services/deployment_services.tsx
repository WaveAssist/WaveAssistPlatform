// fetchEnvironmentsApi, createEnvironmentApi, updateEnvironmentApi, deleteEnvironmentApi
import { callApi } from "./base_service";

// fetchDeploymentsApi
export const fetchDeploymentsApi = async (): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		data_run_key: localStorage.getItem("selected_env_key") || "",
	});
	var path = "manage/fetch_deployments/";
	return callApi(path, body);
};

export const fetchRunningDeploymentApi = async (): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		data_run_key: localStorage.getItem("selected_env_key") || "",
	});
	var path = "manage/fetch_running_deployment/";
	return callApi(path, body);
};

// stopDeploymentApi
export const stopDeploymentApi = async (deploymentKey: string): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		deployment_key: deploymentKey,
		data_run_key: localStorage.getItem("selected_env_key") || "",
	});
	var path = "deploy/stop_deployment/";
	return callApi(path, body);
};
