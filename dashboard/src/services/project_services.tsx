import { callApi, callApiJson, callGetApi } from "./base_service";
import { objectToCsvString } from "../utils/shared_functions";
import { NodeType } from "../utils/types";

export const fetchNodesApi = async (): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
	});
	var path = "manage/fetch_nodes/";
	return callApi(path, body);
};

export const fetchVariablesApi = async (): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		data_run_key: localStorage.getItem("selected_env_key") || "",
	});
	var path = "manage/fetch_project_variables/";
	return callApi(path, body);
};

export const getDataUrl = (key: string): string => {
	const uid = localStorage.getItem("uid") || "";
	const project_key = localStorage.getItem("selected_project_key") || "";
	const data_run_key = localStorage.getItem("selected_env_key") || "";
	const base_url = "https://api.waveassist.io";
	return `${base_url}/data/fetch_data/${uid}/${project_key}/${data_run_key}/${key}`;
};

// FetchPackagesAPI
export const fetchPackagesApi = async (): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
	});
	const path = "debug/fetch_installed_packages/";
	return callApi(path, body);
};

//removePackageApi
export const removePackageApi = async (package_name: string): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		package_name: package_name,
	});
	const path = "debug/uninstall_package/";
	return callApi(path, body);
};

// reinstallPackageApi
export const reinstallPackageApi = async (package_name: string): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		package_name: package_name,
		project_key: localStorage.getItem("selected_project_key") || "",
	});
	const path = "debug/reinstall_package/";
	return callApi(path, body);
};

// installPackageApi
export const installPackageApi = async (package_name: string, package_version?: string): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		package_name: package_name,
		...(package_version && { package_version }),
	});
	const path = "debug/install_package/";
	return callApi(path, body);
};

// createVariableApi
export const createVariableApi = async (variableKey: string, dataType: string): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		data_run_key: localStorage.getItem("selected_env_key") || "",
		data_key: variableKey,
		data_type: dataType,
	});
	var path = "manage/create_data_key/";
	return callApi(path, body);
};

// deleteVariableApi
export const deleteVariableApi = async (variableKey: string): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		data_run_key: localStorage.getItem("selected_env_key") || "",
		data_key: variableKey,
	});
	var path = "manage/delete_data_key/";
	return callApi(path, body);
};

// downloadVariablesApi
export const downloadVariablesApi = async (variableKey: string): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		data_key: variableKey,
		data_run_key: localStorage.getItem("selected_env_key") || "",
	});
	var path = "data/fetch_data_for_key/";
	return callGetApi(path, body);
};

// fetchDataForKeyAPI
export const fetchDataForKeyAPI = async (variableKey: string, runId?: string): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		data_key: variableKey,
		data_run_key: localStorage.getItem("selected_env_key") || "",
	});

	// Add run_id and run_based parameters if runId is provided
	if (runId) {
		body.append("run_id", runId);
		body.append("run_based", "1");
	}

	var path = "data/fetch_data_for_key/";
	return callGetApi(path, body);
};

// uploadVariablesApi
export const uploadVariablesApi = async (csv_data: string, variableKey: string): Promise<any> => {
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		data_key: variableKey,
		data_run_key: localStorage.getItem("selected_env_key") || "",
		data_type: "csv",
		csv_data: csv_data,
	});
	var path = "data/set_data_for_key/";
	return callApi(path, body);
};
export const setDataForKeyApi = async (data: any, data_key: string, data_type: string): Promise<any> => {
	const body = {
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		data_key: data_key,
		data_run_key: localStorage.getItem("selected_env_key") || "",
		data_type: data_type,
		data: data,
	};
	const path = "data/set_data_for_key/";
	return callApiJson(path, body);
};

export const updateCodeApi = async (nodeKey: string, nodeCode: string): Promise<any> => {
	var path = "manage/update_code/";
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		node_key: nodeKey,
		python_code: nodeCode,
		project_key: localStorage.getItem("selected_project_key") || "",
	});
	return callApi(path, body);
};

export const generate_dag_image = async (): Promise<any> => {
	var path = "deploy/generate_dag_image/";
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
	});
	return callApi(path, body);
};

export const createNodeApi = async (data: NodeType): Promise<any> => {
	var path = "manage/create_node/";

	var input_csv = objectToCsvString(data.input_data_key_array, "key");
	var output_csv = objectToCsvString(data.output_data_key_array, "key");
	var run_after_csv = objectToCsvString(data.run_after_nodes_array, "node_key");

	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		name: data.name,
		is_enabled: data.is_enabled ? "1" : "0", // Convert boolean to string "1" or "0"
		is_starting_node: data.is_starting_node ? "1" : "0", // Convert boolean to string "1" or "0"
		schedule_type: data.schedule_type,
		crontab_minutes: data.crontab_minutes,
		crontab_hours: data.crontab_hours,
		crontab_days_of_month: data.crontab_days_of_month,
		crontab_months_of_year: data.crontab_months_of_year,
		crontab_days_of_week: data.crontab_days_of_week,
		crontab_timezone: data.crontab_timezone,
		interval_every: data.interval_every,
		interval_type: data.interval_type,
		input_data_key_csv: input_csv,
		output_data_key_csv: output_csv,
		run_after_nodes_csv: run_after_csv,
	});
	return callApi(path, body);
};

export const updateNodeApi = async (nodeKey: string, data: NodeType): Promise<any> => {
	var path = "manage/update_node/";

	var input_csv = objectToCsvString(data.input_data_key_array, "key");
	var output_csv = objectToCsvString(data.output_data_key_array, "key");
	var run_after_csv = objectToCsvString(data.run_after_nodes_array, "node_key");

	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		node_key: nodeKey,
		name: data.name,
		is_enabled: data.is_enabled ? "1" : "0", // Convert boolean to string "1" or "0"
		is_starting_node: data.is_starting_node ? "1" : "0", // Convert boolean to string "1" or "0"
		schedule_type: data.schedule_type,
		crontab_minutes: data.crontab_minutes,
		crontab_hours: data.crontab_hours,
		crontab_days_of_month: data.crontab_days_of_month,
		crontab_months_of_year: data.crontab_months_of_year,
		crontab_days_of_week: data.crontab_days_of_week,
		crontab_timezone: data.crontab_timezone,
		interval_every: data.interval_every,
		interval_type: data.interval_type,
		input_data_key_csv: input_csv,
		output_data_key_csv: output_csv,
		run_after_nodes_csv: run_after_csv,
	});
	return callApi(path, body);
};

export const deleteNodeApi = async (nodeKey: string): Promise<any> => {
	var path = "manage/delete_node/";
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		node_key: nodeKey,
		project_key: localStorage.getItem("selected_project_key") || "",
	});
	return callApi(path, body);
};

export const runDAGApi = async (nodeKey: string, selected_env: string): Promise<any> => {
	var path = "deploy/run_dag/";
	const body = new URLSearchParams({
		uid: localStorage.getItem("uid") || "",
		project_key: localStorage.getItem("selected_project_key") || "",
		start_node_key: nodeKey,
		data_run_key: selected_env,
	});
	return callApi(path, body);
};

// fetchTemplateApi
export const fetchTemplateApi = async (template_key: string): Promise<any> => {
	const path = `templates/${template_key}/`;
	return callGetApi(path, new URLSearchParams());
};
