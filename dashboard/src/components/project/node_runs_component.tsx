import React, { useEffect, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { fetchNodeRunsApi } from "../../services/runs_services";
import { useToast } from "../../utils/toast_context";
import "./project_components.css";
import "../../utils/ag-theme-project.css";

interface Props {
	dagRunId: string;
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

const NodeRunsComponent: React.FC<Props> = ({ dagRunId }) => {
	const [nodeRunsArray, setNodeRunsArray] = useState<any[]>([]);
	const { showToast } = useToast();

	const fetchNodeRuns = async () => {
		try {
			const data = await fetchNodeRunsApi(dagRunId);
			setNodeRunsArray(data.node_runs || []);
		} catch (error) {
			console.error("fetchNodeRunsApi failed:", error);
			showToast("Something went wrong with loading node runs, please try again.", "danger");
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
			headerName: "Node Name",
			field: "node_name",
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
	];

	return (
		<div className="ag-theme-custom grid-container" style={{ fontSize: "12px" }}>
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
	);
};

export default NodeRunsComponent;
