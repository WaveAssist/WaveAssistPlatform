import React, { useEffect, useState, useCallback } from "react";
import { usePostHog } from "posthog-js/react";
import { AgGridReact } from "ag-grid-react";
import { fetchDagRunsApi } from "../../services/runs_services";
import { fetchDataForKeyAPI, fetchTemplateApi } from "../../services/project_services";
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
	const [isLoading, setIsLoading] = useState(true);
	const { showToast } = useToast();
	const { shouldRefresh } = useRefresh();
	const posthog = usePostHog();

	const fetchRuns = async () => {
		try {
			const data = await fetchDagRunsApi();
			setRunsArray(data.dag_run_array || []);
			setIsLoading(false);
		} catch (error) {
			console.error("fetchDagRunsApi failed:", error);
			showToast("Something went wrong with loading runs, please try again.", "danger");
			setIsLoading(false);
		}
	};

	useEffect(() => {
		fetchRuns();
		const intervalId = setInterval(() => {
			fetchRuns();
		}, 5000); // 10000ms = 10 seconds
		// Clean up the interval when the component unmounts
		return () => clearInterval(intervalId);
	}, [shouldRefresh]);

	// Function to fetch tentative processing time from API
	const fetchTentativeTime = async (runId: string): Promise<number | null> => {
		try {
			const response = await fetchDataForKeyAPI("tentative_time_to_process", runId);
			if (response && response.data) {
				const parsedTime = parseInt(response.data, 10);
				// Only return if it's a valid number
				if (!isNaN(parsedTime) && parsedTime > 0) {
					return parsedTime;
				}
			}
		} catch (error) {
			console.error("Error fetching tentative time:", error);
		}
		// Return null if no valid value
		return null;
	};

	// Effect to update progress for loading runs every 5 seconds
	useEffect(() => {
		const updateProgress = async () => {
			// Get all processing runs
			const processingRuns = runsArray.filter((run) => (run.status === "STARTED" || run.status === "RUNNING") && run.started_at);

			if (processingRuns.length === 0) return;

			// Get current progress state
			setRunProgress((prevProgress) => {
				// Process each run asynchronously
				processingRuns.forEach(async (run) => {
					let totalTime: number | null = prevProgress[run.run_id]?.totalTime || null;
					if (!totalTime) {
						totalTime = await fetchTentativeTime(run.run_id);
					}

					// Only update progress if we have a valid totalTime
					if (totalTime !== null && totalTime > 0) {
						const { progress, remaining } = calculateProgress(run.started_at, totalTime);

						// Update state for this specific run
						setRunProgress((prev) => ({
							...prev,
							[run.run_id]: {
								totalTime,
								progress,
								remaining,
							},
						}));
					}
				});

				return prevProgress;
			});
		};

		// Initial update
		updateProgress();
	}, [runsArray]);

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
	const [loadingOutputRunId, setLoadingOutputRunId] = useState<string | null>(null);
	const [isLoadingRunDetails, setIsLoadingRunDetails] = useState(false);
	const [runProgress, setRunProgress] = useState<Record<string, { totalTime: number; progress: number; remaining: number }>>({});

	const handleLoadingComplete = useCallback(() => {
		console.log("onLoadingComplete called, setting isLoadingRunDetails to false");
		setIsLoadingRunDetails(false);
	}, []);

	// Function to calculate progress based on started_at time
	const calculateProgress = (startedAt: string, totalTime: number) => {
		const startTime = new Date(startedAt).getTime();
		const currentTime = Date.now();
		const elapsedSeconds = Math.floor((currentTime - startTime) / 1000);

		// Cap progress at 80% - never show 90% or 100%
		const progress = Math.min((elapsedSeconds / totalTime) * 100, 80);
		const twenty_percent_time = totalTime * 0.2;
		const remaining = Math.max(totalTime - elapsedSeconds, twenty_percent_time);

		return { progress, remaining };
	};

	// Fetch assistant default message via API
	const fetch_default_message_from_assistant = async (): Promise<string | null> => {
		try {
			const projectData = JSON.parse(localStorage.getItem("selected_project") || "{}");
			const templateKey = projectData.template_key || localStorage.getItem("template_key") || "";
			if (!templateKey) return null;
			const response = await fetchTemplateApi(templateKey);
			const msg = response?.output_default_message;
			if (typeof msg === "string" && msg.trim().length > 0) return msg;
			return null;
		} catch (err) {
			console.error("Failed to fetch assistant default message:", err);
			return null;
		}
	};

	const handleViewDetails = (run: any) => {
		if (run && run.run_id) {
			console.log("Opening View Status modal for run:", run.run_id);
			setIsLoadingRunDetails(true);
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
		setIsLoadingRunDetails(false);
		fetchRuns(); // Refresh data when popup is dismissed
	};

	const handleViewOutput = async (runId: string) => {
		try {
			setLoadingOutputRunId(runId);
			const response = await fetchDataForKeyAPI("display_output", runId);

			if (response && response.data && response.data.html_content) {
				console.log("HTML Content:", response.data.html_content);
				setOutputHtmlContent(response.data.html_content);
				setShowOutputModal(true);
			} else {
				throw new Error("Output data not available.");
			}
		} catch (error) {
			console.error("Error fetching output:", error);
			const run = runsArray.find((r) => r.run_id === runId);
			const isSuccess = run && run.status === "SUCCESS";
			if (isSuccess) {
				const defaultMsg = await fetch_default_message_from_assistant();
				if (defaultMsg && defaultMsg.trim().length > 0) {
					const html = `<h1 style="font-size: 24px;  color: #222222;">${defaultMsg}</h1>`;
					setOutputHtmlContent(html);
					setShowOutputModal(true);
				} else {
					showToast("Output data not available here. Check your email or output target for results.", "warning");
				}
			} else {
				showToast("Output data not available here. Check your email or output target for results.", "warning");
			}
		} finally {
			setLoadingOutputRunId(null);
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
			headerName: "Status",
			field: "status",
			flex: 2,
			minWidth: 120,
			maxWidth: 120,

			resizable: true,
			cellRenderer: (params: any) => {
				const status = params.value === "STARTED" ? "PROCESSING" : params.value;
				const isSuccess = status === "SUCCESS";
				return (
					<span
						className={`badge ${isSuccess ? "badge-primary" : status === "FAILED" ? "badge-danger" : "badge-secondary"}`}
						style={isSuccess ? { backgroundColor: "#1ED66C", color: "#000000" } : {}}>
						{status}
					</span>
				);
			},
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "View Output",
			flex: 2,
			minWidth: 220,
			resizable: true,
			cellRenderer: (params: any) => {
				const status = params.data.status;
				const isSuccess = status === "SUCCESS";
				const isFailed = status === "FAILED";
				const canViewOutput = isSuccess || isFailed;
				const isThisRunLoading = loadingOutputRunId === params.data.run_id;
				const isProcessing = status === "STARTED" || status === "RUNNING";
				const isDisabled = isProcessing || isThisRunLoading;
				const runId = params.data.run_id;
				const progressData = runProgress[runId];

				return (
					<div className="d-flex align-items-center gap-2">
						<button
							className={`btn btn-sm ${isSuccess ? "btn-outline-success" : "btn-outline-secondary"}`}
							onClick={() => canViewOutput && !isThisRunLoading && handleViewOutput(runId)}
							disabled={isDisabled}
							style={
								isSuccess
									? {
											color: "#1ED66C",
											borderColor: "#1ED66C",
											borderRadius: "6px",
									  }
									: { borderRadius: "6px" }
							}
							onMouseEnter={(e) => {
								if (isSuccess && !isDisabled) {
									e.currentTarget.style.backgroundColor = "#1ED66C";
									e.currentTarget.style.color = "#000000";
									e.currentTarget.style.boxShadow = "0 0 20px rgba(30, 214, 108, 0.15)";
								}
							}}
							onMouseLeave={(e) => {
								if (isSuccess && !isDisabled) {
									e.currentTarget.style.backgroundColor = "transparent";
									e.currentTarget.style.color = "#1ED66C";
									e.currentTarget.style.boxShadow = "none";
								}
							}}
							title={canViewOutput ? (isThisRunLoading ? "Loading..." : "View Output") : "Output not available"}>
							{isThisRunLoading ? (
								<>
									<span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
									Loading...
								</>
							) : (
								"View Output"
							)}
						</button>
						{isProcessing && progressData && (
							<div className="d-flex align-items-center gap-2" style={{ fontSize: "11px", color: "#adb5bd" }}>
								<div style={{ position: "relative", width: "40px", height: "40px" }}>
									<svg width="40" height="40" style={{ transform: "rotate(-90deg)" }}>
										{/* Background circle - dark theme */}
										<circle cx="20" cy="20" r="16" fill="none" stroke="#2d3748" strokeWidth="3" />
										{/* Progress circle */}
										<circle
											cx="20"
											cy="20"
											r="16"
											fill="none"
											stroke="#1ED66C"
											strokeWidth="3"
											strokeDasharray={`${(progressData.progress / 100) * 100.53} 100.53`}
											strokeLinecap="round"
										/>
									</svg>
									<div
										style={{
											position: "absolute",
											top: "50%",
											left: "50%",
											transform: "translate(-50%, -50%)",
											fontSize: "8px",
											fontWeight: "bold",
											color: "#1ED66C",
											whiteSpace: "nowrap",
										}}>
										{progressData.progress.toFixed(0)}%
									</div>
								</div>
								<span style={{ whiteSpace: "nowrap" }}>{progressData.remaining.toFixed(0)}s left</span>
							</div>
						)}
					</div>
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
				<button
					className="btn btn-sm btn-outline-secondary"
					onClick={() => handleViewDetails(params.data)}
					title="View Status"
					style={{ borderRadius: "6px" }}>
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
			minWidth: 120,
			resizable: true,
			cellRenderer: (params: any) => formatTimestamp(params.value),
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "Run ID",
			field: "run_id",
			flex: 1,
			minWidth: 150,
			maxWidth: 150,
			resizable: true,
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

					{isLoading && runsArray.length === 0 ? (
						<div className="d-flex justify-content-center align-items-center" style={{ flex: 1, minHeight: "400px" }}>
							<div className="text-center">
								<div
									className="spinner-border mb-3"
									role="status"
									style={{ width: "3rem", height: "3rem", borderColor: "#1ED66C", borderRightColor: "transparent" }}>
									<span className="visually-hidden">Loading...</span>
								</div>
								<div className="text-white">Loading runs...</div>
							</div>
						</div>
					) : (
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
					)}
				</div>
			</div>

			<Modal show={showRunModal} onHide={handleClose} size="lg" centered>
				<Modal.Header closeButton>
					<Modal.Title>Run Details</Modal.Title>
				</Modal.Header>
				<Modal.Body style={{ height: "400px", padding: "0" }}>
					{isLoadingRunDetails && (
						<div
							className="d-flex justify-content-center align-items-center"
							style={{
								height: "400px",
								position: "absolute",
								top: 0,
								left: 0,
								right: 0,
								bottom: 0,
								backgroundColor: "rgba(0,0,0,0.8)",
								zIndex: 1000,
							}}>
							<div className="text-center">
								<div
									className="spinner-border mb-3"
									role="status"
									style={{ width: "3rem", height: "3rem", borderColor: "#1ED66C", borderRightColor: "transparent" }}>
									<span className="visually-hidden">Loading...</span>
								</div>
								<div className="text-white">Loading run details...</div>
							</div>
						</div>
					)}
					{selectedRunId && <NodeRunsComponent dagRunId={selectedRunId} onLoadingComplete={handleLoadingComplete} />}
				</Modal.Body>
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
					{loadingOutputRunId ? (
						<div className="d-flex justify-content-center align-items-center" style={{ minHeight: "400px" }}>
							<div className="text-center">
								<div
									className="spinner-border mb-3"
									role="status"
									style={{ width: "3rem", height: "3rem", borderColor: "#1ED66C", borderRightColor: "transparent" }}>
									<span className="visually-hidden">Loading...</span>
								</div>
								<div className="text-white">Loading output content...</div>
							</div>
						</div>
					) : (
						<>
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
							{outputDisplayMode === "html" && (
								<div className="output-content">{outputHtmlContent && parse(DOMPurify.sanitize(outputHtmlContent))}</div>
							)}

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
											sandbox="allow-same-origin allow-scripts allow-popups allow-popups-to-escape-sandbox"
										/>
									)}
								</div>
							)}
						</>
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
