import React, { useEffect, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { fetchNodeRunsApi } from "../../services/runs_services";
import { fetchRunUsage } from "../../services/account_services";
import { getBrand } from "../../config/branding";
import { useToast } from "../../utils/toast_context";
import "./project_components.css";
import "../../utils/ag-theme-project.css";

const mono = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace";

// Per-run LLM usage strip (model · tokens · cost) from the analytics ledger. Shown only
// where the brand enables it (WaveAssist) and only when the ledger actually has rows.
const RunUsageStrip: React.FC<{ runId: string }> = ({ runId }) => {
	const [usage, setUsage] = useState<any | null>(null);
	useEffect(() => {
		if (!getBrand().showRunUsage || !runId) return;
		const pk = localStorage.getItem("selected_project_key") || "";
		fetchRunUsage(pk, runId)
			.then((d) => setUsage((d?.runs && d.runs[0]) || null))
			.catch(() => {});
	}, [runId]);

	if (!usage || (!usage.cost_usd && !usage.input_tokens && !usage.output_tokens)) return null;
	const pill = (label: string, value: string) => (
		<div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
			<span style={{ fontFamily: mono, fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--color-text-secondary)" }}>{label}</span>
			<span style={{ fontFamily: mono, fontSize: 13, color: "var(--color-text-primary)" }}>{value}</span>
		</div>
	);
	return (
		<div style={{ display: "flex", gap: 28, flexWrap: "wrap", alignItems: "center", padding: "10px 14px", marginBottom: 12, background: "var(--color-bg-card)", border: "1px solid var(--color-border)", borderRadius: 8 }}>
			{usage.models?.length > 0 && pill("Model", usage.models.join(", "))}
			{pill("Tokens in / out", `${usage.input_tokens ?? 0} / ${usage.output_tokens ?? 0}`)}
			{usage.cost_usd ? pill("Cost", `$${Number(usage.cost_usd).toFixed(4)}`) : null}
			{usage.calls ? pill("LLM calls", String(usage.calls)) : null}
		</div>
	);
};

interface Props {
	dagRunId: string;
	onLoadingComplete?: () => void;
}

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

const NodeRunsComponent: React.FC<Props> = ({ dagRunId, onLoadingComplete }) => {
	const [nodeRunsArray, setNodeRunsArray] = useState<any[]>([]);
	const { showToast } = useToast();

	const fetchNodeRuns = async () => {
		try {
			const data = await fetchNodeRunsApi(dagRunId);
			setNodeRunsArray(data.node_runs || []);
		} catch (error) {
			console.error("fetchNodeRunsApi failed:", error);
			showToast("Something went wrong with loading node runs, please try again.", "danger");
		} finally {
			console.log("Calling onLoadingComplete callback");
			onLoadingComplete?.();
		}
	};

	useEffect(() => {
		fetchNodeRuns();
	}, [dagRunId]);

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
			minWidth: 100,
			resizable: true,
			cellRenderer: (params: any) => {
				const status = params.value === "STARTED" ? "PROCESSING" : params.value;
				const isSuccess = status === "SUCCESS";
				return (
					<span
						className={`badge ${isSuccess ? "badge-primary" : status === "FAILED" ? "badge-danger" : "badge-secondary"}`}
						style={isSuccess ? { backgroundColor: "var(--color-primary)", color: "#000000" } : {}}>
						{status}
					</span>
				);
			},
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "Node Name",
			field: "node_name",
			flex: 3,
			minWidth: 140,
			resizable: true,
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
		<div style={{ height: "100%", width: "100%", display: "flex", flexDirection: "column" }}>
			<RunUsageStrip runId={dagRunId} />
			<div className="ag-theme-custom grid-container" style={{ fontSize: "12px", flex: 1, width: "100%" }}>
			<AgGridReact
				rowData={nodeRunsArray}
				columnDefs={columnDefs}
				pagination={true}
				paginationPageSize={10}
				gridOptions={gridOptions}
				defaultColDef={defaultColDef}
				onGridReady={(params) => params.api.sizeColumnsToFit()}
			/>
			</div>
		</div>
	);
};

export default NodeRunsComponent;
