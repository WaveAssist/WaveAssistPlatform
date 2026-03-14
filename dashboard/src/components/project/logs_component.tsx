import React, { useEffect, useState } from "react";
import { fetchLogsApi } from "../../services/logs_services";
import { useToast } from "../../utils/toast_context";
import "./project_components.css";
import { useRefresh } from "../../utils/RefreshContext";
import DarkDropdown from "../../utils/dark_dropdown";
import { fetchNodesApi } from "../../services/project_services";
import { LazyLog, ScrollFollow } from "@melloware/react-logviewer";
import { Button } from "react-bootstrap";
import PaywallBlock from "../PaywallBlock";
import { hasBuilderAccess } from "../../utils/plan";

const LogsComponent: React.FC = () => {
	const { shouldRefresh } = useRefresh();
	const [logString, setLogString] = useState<string>("");
	const [loading, setLoading] = useState(true);
	const { showToast } = useToast();
	const [nodesArray, setNodesArray] = useState<any[]>([]);
	const [selectedSystemKey, _] = useState("celery-worker");
	const [selectedNodeKey, setSelectedNodeKey] = useState("All");

	// Only builder can access Logs (editor and operator cannot)
	const isBuilderPlan = hasBuilderAccess();
	const shouldBlockLogs = !isBuilderPlan;
	// const systemName = ["Worker", "API", "Redis", "MongoDB", "Dashboard"];
	// const systemKeys = ["celery-worker", "django", "redis", "mongodb", "dashboard"];

	// const systemName = ["Worker"];
	// const systemKeys = ["celery-worker"];

	//Selected system
	// const handleSystemChange = async (_system_name: string, system_key: string) => {
	// 	setSelectedSystemKey(system_key);
	// };

	const getSelectedNodeName = () => {
		const index = nodesArray.findIndex((node) => node.node_key === selectedNodeKey);
		return index >= 0 ? nodesArray[index].name : "All Nodes";
	};

	const handleNodeChange = async (_node_name: string, node_key: string) => {
		setSelectedNodeKey(node_key);
	};

	// const getSelectedSystemName = () => {
	// 	const index = systemKeys.indexOf(selectedSystemKey);
	// 	return index >= 0 ? systemName[index] : "Select System";
	// };
	const fetchNodes = async () => {
		try {
			const data = await fetchNodesApi();
			setNodesArray(data.node_array);
			setLoading(false);
		} catch (error) {
			console.error("FetchNodesApi failed:", error);
			showToast("Something went wrong with loading Nodes, please try again.", "danger");
			setLoading(false);
		}
	};

	const fetchLogs = async () => {
		try {
			const data = await fetchLogsApi(selectedSystemKey, selectedNodeKey, nodesArray);
			const logs = data.logs;
			var logsAsString = logs
				.filter((log: any) => log.timestamp && log.log) // Ensure valid logs
				.sort((a: any, b: any) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()) // Sort by timestamp in reverse order
				.map((log: any) => `${log.timestamp} - ${log.log}`)
				.join("\n");
			setLogString(logsAsString);
		} catch (error) {
			console.error("fetchLogsApi failed:", error);
			showToast("Something went wrong with loading logs, trying again...", "warning");
		}
	};

	useEffect(() => {
		fetchNodes();
	}, [shouldRefresh]);

	useEffect(() => {
		if (nodesArray.length > 0) {
			fetchLogs();
			const intervalId = setInterval(() => {
				fetchLogs();
			}, 10000); // 5000ms = 5 seconds
			// Clean up the interval when the component unmounts
			return () => clearInterval(intervalId);
		}
	}, [nodesArray, selectedSystemKey, selectedNodeKey]); // Dependencies to rerun on change

	return (
		<div className="main-container">
			<PaywallBlock show={shouldBlockLogs} showUpgradeButton={!isBuilderPlan} />
			<div className="mt-3 d-flex flex-column" style={{ height: "100%" }}>
				<div style={{ flex: "0 0 100%", display: "flex", flexDirection: "column" }}>
					<div className="d-flex justify-content-start align-items-center mb-3">
						<h3 className="translucent_white">Logs</h3>
						<div className="ms-auto d-flex">
							{/* <DarkDropdown
								items={systemName}
								keys={systemKeys}
								defaultText={getSelectedSystemName()}
								headerText="Select System"
								onItemSelect={handleSystemChange}
							/> */}
							{selectedSystemKey === "celery-worker" && (
								<DarkDropdown
									items={["All Nodes", ...nodesArray.map((node) => node.name), "Raw Logs"]}
									keys={[
										"All", // CSV of all node keys for "All Nodes"
										...nodesArray.map((node) => node.node_key),
										"",
									]}
									defaultText={getSelectedNodeName()}
									headerText="Select Node"
									onItemSelect={handleNodeChange}
								/>
							)}

							<Button variant="dark" onClick={fetchLogs}>
								<span className="bi bi-arrow-clockwise"></span>
							</Button>
						</div>
					</div>

					{loading && nodesArray.length === 0 ? (
						<div className="d-flex justify-content-center align-items-center" style={{ flex: 1, minHeight: "400px" }}>
							<div className="text-center">
								<div className="spinner-border text-success mb-3" role="status" style={{ width: "3rem", height: "3rem" }}>
									<span className="visually-hidden">Loading...</span>
								</div>
								<div className="text-white">Loading logs...</div>
							</div>
						</div>
					) : (
						<div className={`${location.pathname === "/manage/logs" ? "log-container" : "log-container-runs"} bg_color_dark`}>
							<ScrollFollow
								startFollowing={true}
								render={({ follow, onScroll }) => (
									<LazyLog
										text={logString || "...................."}
										enableSearch
										caseInsensitive
										extraLines={2}
										selectableLines={true}
										follow={follow}
										onScroll={onScroll}
									/>
								)}
							/>
						</div>
					)}
				</div>
			</div>
		</div>
	);
};

export default LogsComponent;
