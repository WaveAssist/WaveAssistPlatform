import React, { useEffect, useState } from "react";
import { usePostHog } from "posthog-js/react";
import { AgGridReact } from "ag-grid-react";
import { fetchDagRunsApi } from "../../services/runs_services";
import { useToast } from "../../utils/toast_context";
import { useRefresh } from "../../utils/RefreshContext";
import Modal from "react-bootstrap/Modal";
import { Button } from "react-bootstrap";
import NodeRunsComponent from "./node_runs_component";
import "./project_components.css";
import "../../utils/ag-theme-project.css";

const formatTimestamp = (timestamp: string) => {
	if (!timestamp) return "";
	const date = new Date(timestamp);
	const datePart = date.toLocaleDateString([], { month: "2-digit", day: "2-digit" });
	const timePart = date.toLocaleTimeString([], {
		hour12: false,
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit",
	});
	const milliseconds = date.getMilliseconds().toString().padStart(3, "0");
	return `${datePart} ${timePart}.${milliseconds}`;
};

const RunsComponent: React.FC = () => {
	const [runsArray, setRunsArray] = useState<any[]>([]);
	const { showToast } = useToast();
	const { shouldRefresh } = useRefresh();
	const posthog = usePostHog();

	const fetchRuns = async () => {
		try {
			const data = await fetchDagRunsApi();
			setRunsArray(data.dag_run_array || []);
		} catch (error) {
			console.error("fetchDagRunsApi failed:", error);
			showToast("Something went wrong with loading runs, please try again.", "danger");
		}
	};

	useEffect(() => {
		fetchRuns();
		const intervalId = setInterval(() => {
			fetchRuns();
		}, 10000); // 10000ms = 10 seconds
		// Clean up the interval when the component unmounts
		return () => clearInterval(intervalId);
	}, [shouldRefresh]);

	useEffect(() => {
		// Pageview context for runs list
		try {
			posthog?.capture("$pageview", {
				page_category: "runs",
				project_id: localStorage.getItem("selected_project_key") || undefined,
				environment: localStorage.getItem("selected_env_key") || undefined,
			});
		} catch (_err) {}
	}, []);

	const [showRunModal, setShowRunModal] = useState(false);
	const [selectedRunId, setSelectedRunId] = useState("");

	const handleViewDetails = (run: any) => {
		if (run && run.run_id) {
			setSelectedRunId(run.run_id);
			setShowRunModal(true);
			try {
				posthog?.capture("run_viewed", {
					project_id: localStorage.getItem("selected_project_key") || undefined,
					environment: localStorage.getItem("selected_env_key") || undefined,
					run_id: run.run_id,
				});
			} catch (_err) {}
		}
	};

	const handleClose = () => {
		setSelectedRunId("");
		setShowRunModal(false);
	};

	const gridOptions = {
		suppressCellFocus: true,
	};

	const defaultColDef = {
		autoHeight: true,
		wrapText: true,
		enableCellChangeFlash: true,
		editable: false,
		cellClass: "ag-cell",
	};

	const columnDefs = [
		{
			headerName: "Run ID",
			field: "run_id",
			flex: 3,
			minWidth: 120,
			resizable: true,
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "Started At",
			field: "started_at",
			flex: 3,
			minWidth: 150,
			resizable: true,
			cellRenderer: (params: any) => formatTimestamp(params.value),
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "Finished At",
			field: "finished_at",
			flex: 3,
			minWidth: 150,
			resizable: true,
			cellRenderer: (params: any) => formatTimestamp(params.value),
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "Duration",
			flex: 2,
			minWidth: 100,
			resizable: true,
			cellRenderer: (params: any) => {
				const { started_at, finished_at } = params.data;
				if (started_at && finished_at) {
					const diffMs = new Date(finished_at).getTime() - new Date(started_at).getTime();
					if (diffMs >= 1000) {
						return `${(diffMs / 1000).toFixed(2)} s`;
					}
					return `${diffMs} ms`;
				}
				return "NA";
			},
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "Status",
			field: "status",
			flex: 2,
			minWidth: 100,
			resizable: true,
			cellRenderer: (params: any) => (
				<span className={`badge ${params.value === "SUCCESS" ? "badge-primary" : params.value === "FAILED" ? "badge-danger" : "badge-secondary"}`}>
					{params.value}
				</span>
			),
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "Actions",
			flex: 2,
			minWidth: 120,
			resizable: true,
			cellRenderer: (params: any) => (
				<button className="btn btn-outline-success btn-sm" onClick={() => handleViewDetails(params.data)}>
					View Details
				</button>
			),
			cellStyle: { display: "flex", alignItems: "center" },
		},
	];

	return (
		<div className="main-container">
			<div className="mt-3 d-flex flex-column" style={{ height: "100%" }}>
				<div style={{ flex: "0 0 40%", display: "flex", flexDirection: "column" }}>
					<div className="d-flex justify-content-between align-items-center mb-3">
						<h3 className="translucent_white mb-0">Runs</h3>
						<Button variant="dark" onClick={fetchRuns}>
							<span className="bi bi-arrow-clockwise"></span>
						</Button>
					</div>
					<div className="ag-theme-custom grid-container" style={{ flex: 1 }}>
						<AgGridReact
							rowData={runsArray}
							columnDefs={columnDefs}
							pagination={false}
							paginationPageSize={10}
							gridOptions={gridOptions}
							defaultColDef={defaultColDef}
						/>
					</div>
				</div>
				
			</div>

			<Modal show={showRunModal} onHide={handleClose} size="lg" centered>
				<Modal.Header closeButton>
					<Modal.Title>Run Details</Modal.Title>
				</Modal.Header>
				<Modal.Body>
					{/* {selectedRunId && <NodeRunsComponent dagRunId={selectedRunId} />} */}
					<div style={{ height: "400px", width: "100%" }} className="ag-theme-custom">
						{selectedRunId && <NodeRunsComponent dagRunId={selectedRunId} />}
					</div>
				</Modal.Body>
				<Modal.Footer>
					<Button variant="secondary" onClick={handleClose}>
						Close
					</Button>
				</Modal.Footer>
			</Modal>
		</div>
	);
};

export default RunsComponent;
