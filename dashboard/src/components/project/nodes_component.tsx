import React, { useEffect, useState } from "react";
import { fetchNodesApi } from "../../services/project_services";
import { useToast } from "../../utils/toast_context";
import { Button } from "react-bootstrap";
import { AgGridReact } from "ag-grid-react";
import "./project_components.css";
import type { GridOptions } from "ag-grid-community";
import "../../utils/ag-grid-theme-builder.css";

const NodesComponent: React.FC = () => {
	const [nodesArray, setNodesArray] = useState<any[]>([]);
	const { showToast } = useToast();

	const fetchNodes = async () => {
		try {
			const data = await fetchNodesApi();
			setNodesArray(data.node_array);
		} catch (error) {
			console.error("FetchNodesApi failed:", error);
			showToast("Something went wrong with loading Nodes, please try again.", "danger");
		}
	};
	const gridOptions: GridOptions = {
		suppressCellFocus: true,
	};

	useEffect(() => {
		fetchNodes();
	}, []);

	const handleViewCode = (node: any) => {
		console.log("View Code:", node);
	};

	const handleEdit = (node: any) => {
		console.log("Edit:", node);
	};

	const handleDelete = (node: any) => {
		console.log("Delete:", node);
	};

	const handleRun = (node: any) => {
		console.log("Run:", node);
	};

	const ViewCodeButton = (params: any) => (
		<button className="btn btn-outline-success btn-sm" onClick={() => handleViewCode(params.data)}>
			View Code
		</button>
	);

	const ActionButtons = (params: any) => {
		return (
			<div>
				<Button variant="dark" size="sm" onClick={() => handleEdit(params.data)}>
					<i className="bi bi-pencil"></i>
				</Button>{" "}
				<Button variant="primary" size="sm" onClick={() => handleRun(params.data)}>
					<i className="bi bi-play"></i>
				</Button>{" "}
				<Button variant="danger" size="sm" onClick={() => handleDelete(params.data)}>
					<i className="bi bi-trash"></i>
				</Button>
			</div>
		);
	};

	const formatSchedule = (data: any) => {
		if (data.schedule_type === "crontab") {
			const cleanedCrontabSchedule = data.crontab_schedule.replace(/\(.*?\)/g, "");
			return (
				<div>
					<span className="badge badge-primary">Cron</span> <span className="badge badge-secondary">{cleanedCrontabSchedule}</span>
				</div>
			);
		} else if (data.schedule_type === "interval") {
			return (
				<div>
					<span className="badge badge-primary">Interval</span> <span className="badge badge-secondary">{data.interval_schedule}</span>
				</div>
			);
		} else if (data.schedule_type === "none") {
			return (
				<div>
					<span className="badge badge-primary">Runs After</span>{" "}
					{data.run_after_nodes_array.map((node: any) => (
						<span key={node.name} className="badge badge-secondary">
							{node.name}
						</span>
					))}
				</div>
			);
		}
		return <div></div>;
	};

	const defaultColDef = {
		autoHeight: true,
		wrapText: true,
		enableCellChangeFlash: true,
		editable: false,
		cellClass: "ag-cell",
	};

	const columnDefs = [
		{ headerName: "Name", field: "name", width: 200 },
		{
			headerName: "Status",
			field: "is_enabled",
			cellRenderer: (params: any) => (
				<span className={`badge ${params.value ? "badge-primary" : "badge-danger"}`}>{params.value ? "Enabled" : "Disabled"}</span>
			),
			width: 100,
		},
		{
			headerName: "Input",
			field: "input_data_key_array",
			cellRenderer: (params: any) => (
				<div>
					{params.value.map((v: any) => (
						<span className="badge badge-secondary m-1 " key={v.key}>
							{v.key}
						</span>
					))}
				</div>
			),
			width: 200,
		},
		{
			headerName: "Output",
			field: "output_data_key_array",
			cellRenderer: (params: any) => (
				<div>
					{params.value.map((v: any) => (
						<span className="badge badge-secondary m-1" key={v.key}>
							{v.key}
						</span>
					))}
				</div>
			),
			width: 200,
		},
		{
			headerName: "Scheduled",
			width: 200,
			cellRenderer: (params: any) => formatSchedule(params.data),
		},
		{ headerName: "Code", cellRenderer: ViewCodeButton, width: 120 },
		{ headerName: "Actions", cellRenderer: ActionButtons, width: 140 },
	];

	return (
		<div className="main-container">
			<div className="mt-3">
				<div className="d-flex justify-content-between align-items-center mb-3 ">
					<h3 className="translucent_white">Nodes</h3>
					<Button variant="dark">
						<span className="bi bi-plus-lg"></span>
					</Button>
				</div>
				<div className="ag-theme-custom grid-container">
					<AgGridReact
						rowData={nodesArray}
						columnDefs={columnDefs}
						pagination={true}
						paginationPageSize={10}
						gridOptions={gridOptions}
						defaultColDef={defaultColDef}
					/>
				</div>
			</div>
		</div>
	);
};

export default NodesComponent;
