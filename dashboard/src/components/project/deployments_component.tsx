import React, { useEffect, useState } from "react";
import { fetchDeploymentsApi, stopDeploymentApi } from "../../services/deployment_services";
import { useToast } from "../../utils/toast_context";
import { Button } from "react-bootstrap";
import { AgGridReact } from "ag-grid-react";
import "./project_components.css";
import "../../utils/ag-theme-project.css";
import { useRefresh } from "../../utils/RefreshContext";

const DeploymentsComponent: React.FC = () => {
	const [deploymentsArray, setDeploymentsArray] = useState<any[]>([]);
	const { showToast } = useToast();
	const { shouldRefresh } = useRefresh();

	const fetchDeployments = async () => {
		try {
			const data = await fetchDeploymentsApi();
			setDeploymentsArray(data.deployment_array);
		} catch (error) {
			console.error("fetchDeploymentsApi failed:", error);
			showToast("Something went wrong with loading deployments, please try again.", "danger");
		}
	};

	const handleStopDeployment = async (deployment: any) => {
		const confirmStop = window.confirm("Are you sure you want to stop this deployment?");
		if (!confirmStop) {
			return;
		}
		try {
			await stopDeploymentApi(deployment.key);
			showToast("Deployment stopped successfully.", "success");
			fetchDeployments();
		} catch (error) {
			console.error("stopDeploymentApi failed:", error);
			showToast("" + error, "danger");
		}
	};

	const gridOptions = {
		suppressCellFocus: true,
	};

	useEffect(() => {
		fetchDeployments();
	}, [shouldRefresh]);

	const ActionButtons = (params: any) => {
		return (
			//Keep an active button if deployment is running

			<div>
				{params.data.is_running && (
					<Button variant="danger" size="sm" onClick={() => handleStopDeployment(params.data)}>
						<i className="bi bi-stop-fill"></i> Stop
					</Button>
				)}
				{!params.data.is_running && (
					<Button variant="secondary" size="sm" disabled>
						<i className="bi bi-stop-fill"></i> Stop
					</Button>
				)}
			</div>
		);
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
			headerName: "Deployment Key",
			field: "key",
			flex: 3,
			minWidth: 150,
			resizable: true,
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "Version",
			field: "version",
			flex: 2,
			minWidth: 100,
			resizable: true,
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "Running Status",
			field: "is_running",
			cellRenderer: (params: any) => (
				<span className={`badge ${params.value ? "badge-primary" : "badge-secondary"}`}>{params.value ? "Running" : "Stopped"}</span>
			),
			flex: 2,
			minWidth: 120,
			resizable: true,
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "Actions",
			cellRenderer: ActionButtons,
			flex: 2,
			minWidth: 100,
			resizable: true,
			cellStyle: { display: "flex", alignItems: "center" },
		},
	];

	return (
		<div className="main-container">
			<div className="mt-3">
				<div className="d-flex justify-content-between align-items-center mb-3">
					<h3 className="translucent_white">Deployments</h3>
				</div>
				<div className="ag-theme-custom grid-container">
					<AgGridReact
						rowData={deploymentsArray}
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

export default DeploymentsComponent;
