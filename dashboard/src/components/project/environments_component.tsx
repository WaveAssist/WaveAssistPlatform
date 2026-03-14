import React, { useEffect, useState } from "react";
import { fetchEnvironmentsApi, createEnvironmentApi, updateEnvironmentApi, deleteEnvironmentApi } from "../../services/environment_services";
import { useToast } from "../../utils/toast_context";
import { Button, Form } from "react-bootstrap";
import { AgGridReact } from "ag-grid-react";
import "./project_components.css";
import "../../utils/ag-theme-project.css";
import Modal from "react-bootstrap/Modal";
import { useRefresh } from "../../utils/RefreshContext";
import PaywallBlock from "../PaywallBlock";
import { hasBuilderAccess } from "../../utils/plan";

const EnvironmentsComponent: React.FC = () => {
	const [environmentsArray, setEnvironmentsArray] = useState<any[]>([]);
	const { showToast } = useToast();
	const [showEnvironmentEditor, setShowEnvironmentEditor] = useState(false);
	const [environmentData, setEnvironmentData] = useState({ name: "", is_enabled: false });
	const [editingEnvironmentKey, setEditingEnvironmentKey] = useState("");
	const { shouldRefresh } = useRefresh();
	const [loading, setLoading] = useState(true);

	// Only builder can access Environments (editor and operator cannot)
	const isBuilderPlan = hasBuilderAccess();
	const shouldBlockEnvironments = !isBuilderPlan;

	const handleCloseEnvironmentEditor = () => {
		setShowEnvironmentEditor(false);
		setEnvironmentData({ name: "", is_enabled: false });
		setEditingEnvironmentKey("");
	};

	const fetchEnvironments = async () => {
		setLoading(true);
		try {
			const data = await fetchEnvironmentsApi();
			setEnvironmentsArray(data.environment_array);
		} catch (error) {
			console.error("fetchEnvironmentsApi failed:", error);
			showToast("Something went wrong with loading environments, please try again.", "danger");
		} finally {
			setLoading(false);
		}
	};

	const handleShowEnvironmentEditor = (environment: any = null) => {
		if (environment) {
			setEnvironmentData({ name: environment.name, is_enabled: environment.is_enabled });
			setEditingEnvironmentKey(environment.key);
		} else {
			setEnvironmentData({ name: "", is_enabled: false });
		}
		setShowEnvironmentEditor(true);
	};

	const handleCreateOrUpdateEnvironment = async () => {
		try {
			if (editingEnvironmentKey) {
				await updateEnvironmentApi(editingEnvironmentKey, environmentData);
				showToast("Environment updated successfully.", "success");
			} else {
				await createEnvironmentApi(environmentData);
				showToast("Environment created successfully.", "success");
			}
			fetchEnvironments();
			handleCloseEnvironmentEditor();
		} catch (error) {
			console.error("Environment API failed:", error);
			showToast("" + error, "danger");
		}
	};

	const handleDeleteEnvironment = async (environment: any) => {
		const confirmDelete = window.confirm("Are you sure you want to delete this environment? This action cannot be undone.");
		if (!confirmDelete) {
			return;
		}
		try {
			await deleteEnvironmentApi(environment.key);
			showToast("Environment deleted successfully.", "success");
			fetchEnvironments();
		} catch (error) {
			console.error("deleteEnvironmentApi failed:", error);
			showToast("" + error, "danger");
		}
	};

	const gridOptions = {
		suppressCellFocus: true,
	};

	useEffect(() => {
		fetchEnvironments();
	}, [shouldRefresh]);

	const ActionButtons = (params: any) => {
		return (
			<div>
				<Button variant="dark" size="sm" onClick={() => handleShowEnvironmentEditor(params.data)} className="me-3">
					<i className="bi bi-pencil"></i>
				</Button>
				<Button variant="danger" size="sm" onClick={() => handleDeleteEnvironment(params.data)}>
					<i className="bi bi-trash"></i>
				</Button>
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
			headerName: "Environment Name",
			field: "name",
			flex: 3,
			minWidth: 150,
			resizable: true,
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "Key",
			field: "key",
			cellRenderer: (params: any) => <span className="badge badge-secondary">{params.value}</span>,
			flex: 3,
			minWidth: 120,
			resizable: true,
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "Status",
			field: "is_enabled",
			cellRenderer: (params: any) => (
				<span className={`badge ${params.value ? "badge-primary" : "badge-danger"}`}>{params.value ? "Enabled" : "Disabled"}</span>
			),
			flex: 2,
			minWidth: 100,
			resizable: true,
			cellStyle: { display: "flex", alignItems: "center" },
		},
		{
			headerName: "Actions",
			cellRenderer: ActionButtons,
			flex: 2,
			minWidth: 120,
			resizable: true,
			cellStyle: { display: "flex", alignItems: "center" },
		},
	];

	return (
		<div className="main-container">
			<PaywallBlock show={shouldBlockEnvironments} showUpgradeButton={!isBuilderPlan} />
			<div className="mt-3 d-flex flex-column" style={{ height: "100%" }}>
				<div style={{ flex: "0 0 100%", display: "flex", flexDirection: "column" }}>
					<div className="d-flex justify-content-between align-items-center mb-3">
						<h3 className="translucent_white">Environments</h3>
						<div>
							<Button variant="dark" onClick={() => handleShowEnvironmentEditor()}>
								<span className="bi bi-plus-lg"></span>
							</Button>
						</div>
					</div>

					{loading && environmentsArray.length === 0 ? (
						<div className="d-flex justify-content-center align-items-center" style={{ flex: 1, minHeight: "400px" }}>
							<div className="text-center">
								<div className="spinner-border text-success mb-3" role="status" style={{ width: "3rem", height: "3rem" }}>
									<span className="visually-hidden">Loading...</span>
								</div>
								<div className="text-white">Loading environments...</div>
							</div>
						</div>
					) : (
						<div className="ag-theme-custom grid-container">
							<AgGridReact
								rowData={environmentsArray}
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

			<Modal show={showEnvironmentEditor} onHide={handleCloseEnvironmentEditor} size="lg" centered>
				<Modal.Header closeButton>
					<Modal.Title>{editingEnvironmentKey ? "Edit Environment" : "Create Environment"}</Modal.Title>
				</Modal.Header>
				<Modal.Body>
					<Form.Group controlId="environmentName">
						<Form.Label>Environment Name</Form.Label>
						<Form.Control
							type="text"
							value={environmentData.name}
							onChange={(e) => setEnvironmentData({ ...environmentData, name: e.target.value })}
							required
						/>
					</Form.Group>
					<br />
					<Form.Group controlId="environmentStatus">
						<Form.Check
							type="checkbox"
							label="Enabled"
							checked={environmentData.is_enabled}
							onChange={(e) => setEnvironmentData({ ...environmentData, is_enabled: e.target.checked })}
						/>
					</Form.Group>
					<br />
					<Modal.Footer>
						<Button variant="secondary" onClick={handleCloseEnvironmentEditor}>
							Close
						</Button>
						<Button variant="primary" onClick={handleCreateOrUpdateEnvironment}>
							{editingEnvironmentKey ? "Update" : "Create"}
						</Button>
					</Modal.Footer>
				</Modal.Body>
			</Modal>
		</div>
	);
};

export default EnvironmentsComponent;
