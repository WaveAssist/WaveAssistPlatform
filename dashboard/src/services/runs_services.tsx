import { callApi } from "./base_service";

export const fetchDagRunsApi = async (): Promise<any> => {
    const body = new URLSearchParams({
        uid: localStorage.getItem("uid") || "",
        project_key: localStorage.getItem("selected_project_key") || "",
        data_run_key: localStorage.getItem("selected_env_key") || "",
    });
    const path = "runs/fetch_dag_runs/";
    return callApi(path, body);
};

export const fetchNodeRunsApi = async (dag_run_id: string): Promise<any> => {
    const body = new URLSearchParams({
        uid: localStorage.getItem("uid") || "",
        project_key: localStorage.getItem("selected_project_key") || "",
        data_run_key: localStorage.getItem("selected_env_key") || "",
        dag_run_id: dag_run_id,
    });
    const path = "runs/fetch_node_runs/";
    return callApi(path, body);
};
