import React, { useEffect, useState } from "react";
import { usePostHog } from "posthog-js/react";
import { AgGridReact } from "ag-grid-react";
import { fetchDagRunsApi } from "../../services/runs_services";
import { fetchDataForKeyAPI } from "../../services/project_services";
import { useToast } from "../../utils/toast_context";
import { useRefresh } from "../../utils/RefreshContext";
import Modal from "react-bootstrap/Modal";
import { Button } from "react-bootstrap";
import NodeRunsComponent from "./node_runs_component";
import parse from "html-react-parser";
import DOMPurify from "dompurify";
import html2pdf from "html2pdf.js";
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
	const [showOutputModal, setShowOutputModal] = useState(false);
	const [outputHtmlContent, setOutputHtmlContent] = useState("");
	const [outputDisplayMode, setOutputDisplayMode] = useState<"html" | "iframe">("iframe");

	const handleViewDetails = (run: any) => {
		if (run && run.run_id) {
			setSelectedRunId(run.run_id);
			setShowRunModal(true);
			fetchRuns(); // Refresh data when popup is opened
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
		fetchRuns(); // Refresh data when popup is dismissed
	};

	const handleViewOutput = async (runId: string) => {
		try {
			console.log("View Output clicked for run ID:", runId);
			const response = await fetchDataForKeyAPI("display_output", runId);
			console.log("Output data:", response);

			if (response && response.data && response.data.html_content) {
				console.log("HTML Content:", response.data.html_content);
				setOutputHtmlContent(response.data.html_content);
				setShowOutputModal(true);
			} else {
				showToast("No output content available", "warning");
			}
		} catch (error) {
			console.error("Error fetching output:", error);
			showToast("Output data not available here. Check your email or output target for results.", "warning");
		}
	};

	const handleDownloadPDF = async () => {
		try {
			// Create a temporary div to hold the HTML content
			const tempDiv = document.createElement("div");
			tempDiv.innerHTML = outputHtmlContent;
			tempDiv.style.padding = "20px";
			tempDiv.style.fontFamily = "Arial, sans-serif";
			tempDiv.style.fontSize = "12px";
			tempDiv.style.lineHeight = "1.4";

			// Configure PDF options
			const options = {
				margin: 10,
				filename: `waveassist_run_output_${Date.now()}.pdf`,
				image: { type: "jpeg", quality: 0.98 },
				html2canvas: {
					scale: 2,
					useCORS: true,
					allowTaint: true,
				},
				jsPDF: {
					unit: "mm",
					format: "a4",
					orientation: "portrait",
				},
			};

			// Generate and download PDF
			await html2pdf().from(tempDiv).set(options).save();
			showToast("PDF downloaded successfully", "success");
		} catch (error) {
			console.error("Error generating PDF:", error);
			showToast("Failed to generate PDF", "danger");
		}
	};

	const handleDisplayModeChange = () => {
		setOutputDisplayMode(outputDisplayMode === "iframe" ? "html" : "iframe");
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
			flex: 1,
			minWidth: 50,
			maxWidth: 150,
			resizable: true,
			pinned: "left" as const,
			cellRenderer: (params: any) => {
				const runId = params.value;
				if (!runId) return "";

				// Truncate to first 3 and last 3 characters
				const truncated = runId.length > 8 ? `${runId.substring(0, 4)}...${runId.substring(runId.length - 4)}` : runId;

				const handleCopy = () => {
					navigator.clipboard.writeText(runId);
					// Optional: Show a toast notification
					showToast("Run ID copied to clipboard", "success");
				};

				return (
					<div className="d-flex align-items-center gap-1" style={{ cursor: "pointer" }} onClick={handleCopy} title={`Click to copy: ${runId}`}>
						<span className="text-truncate">{truncated}</span>
						<span className="bi bi-clipboard" style={{ fontSize: "12px", opacity: 0.7 }}></span>
					</div>
				);
			},
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "Status",
			field: "status",
			flex: 2,
			minWidth: 100,
			resizable: true,
			cellRenderer: (params: any) => {
				const status = params.value === "STARTED" ? "RUNNING" : params.value;
				return (
					<span className={`badge ${status === "SUCCESS" ? "badge-primary" : status === "FAILED" ? "badge-danger" : "badge-secondary"}`}>
						{status}
					</span>
				);
			},
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "View Output",
			flex: 2,
			minWidth: 130,
			resizable: true,
			cellRenderer: (params: any) => {
				const isSuccess = params.data.status === "SUCCESS";
				const isDisabled = params.data.status === "STARTED" || params.data.status === "RUNNING" || params.data.status === "FAILED";

				return (
					<button
						className={`btn btn-sm ${isSuccess ? "btn-outline-success" : "btn-outline-secondary"}`}
						onClick={() => isSuccess && handleViewOutput(params.data.run_id)}
						disabled={isDisabled}
						title={isSuccess ? "View Output" : "Output not available"}>
						View Output
					</button>
				);
			},
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "View Status",
			flex: 2,
			minWidth: 130,
			resizable: true,
			cellRenderer: (params: any) => (
				<button className="btn btn-sm btn-outline-secondary" onClick={() => handleViewDetails(params.data)} title="View Status">
					View Status
				</button>
			),
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
	];

	return (
		<div className="main-container">
			<div className="mt-3 d-flex flex-column" style={{ height: "100%" }}>
				<div style={{ flex: "0 0 100%", display: "flex", flexDirection: "column" }}>
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
							pagination={true}
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
				<Modal.Body style={{ height: "400px", padding: "0" }}>{selectedRunId && <NodeRunsComponent dagRunId={selectedRunId} />}</Modal.Body>
				<Modal.Footer>
					<Button variant="secondary" onClick={handleClose}>
						Close
					</Button>
				</Modal.Footer>
			</Modal>

			<Modal show={showOutputModal} onHide={() => setShowOutputModal(false)} size="xl" centered>
				<Modal.Header closeButton>
					<Modal.Title>Run Output</Modal.Title>
				</Modal.Header>
				<Modal.Body style={{ maxHeight: "80vh", overflow: "auto" }}>
					{/* Display Mode Toggle Buttons */}
					<div className="d-flex justify-content-end gap-2 mb-3">
						<Button variant="outline-success" size="sm" onClick={handleDisplayModeChange}>
							{outputDisplayMode === "iframe" ? "Reader View" : "Default View"}
						</Button>
						<Button variant="outline-success" size="sm" onClick={handleDownloadPDF} title="Download as PDF">
							<span className="bi bi-download me-1"></span>
							Download
						</Button>
					</div>

					{/* Content Display */}
					{outputDisplayMode === "html" && <div className="output-content">{outputHtmlContent && parse(DOMPurify.sanitize(outputHtmlContent))}</div>}

					{outputDisplayMode === "iframe" && (
						<div className="output-content">
							{outputHtmlContent && (
								<iframe
									srcDoc={outputHtmlContent}
									style={{
										width: "100%",
										height: "60vh",
										border: "1px solid #ddd",
										borderRadius: "4px",
										backgroundColor: "white",
									}}
									title="Run Output"
									sandbox="allow-same-origin allow-scripts"
								/>
							)}
						</div>
					)}
				</Modal.Body>
				<Modal.Footer>
					<Button variant="secondary" onClick={() => setShowOutputModal(false)}>
						Close
					</Button>
				</Modal.Footer>
			</Modal>
		</div>
	);
};

export default RunsComponent;
