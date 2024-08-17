import React, { useEffect, useState } from "react";
import { fetchVariablesApi, createVariableApi, deleteVariableApi, downloadVariablesApi, uploadVariablesApi } from "../../services/project_services";
import { useToast } from "../../utils/toast_context";
import { Button, Spinner } from "react-bootstrap";
import { AgGridReact } from "ag-grid-react";
import "./project_components.css";
import "../../utils/ag-theme-project.css";
import Modal from "react-bootstrap/Modal";
import { downloadFile } from "../../utils/shared_functions";
import { useRefresh } from "../../utils/RefreshContext";
import { useNavigate } from "react-router-dom";

const VariablesComponent: React.FC = () => {
	const [variablesArray, setVariablesArray] = useState<any[]>([]);
	const { showToast } = useToast();
	const [showVariableEditor, setShowVariableEditor] = useState(false);
	const [loading, setLoading] = useState(false);
	const [variableKey, setVariableKey] = useState("");
	const { shouldRefresh } = useRefresh();
	const navigate = useNavigate();

	const handleCloseVariableEditor = () => {
		setShowVariableEditor(false);
	};

	const fetchVariables = async () => {
		try {
			const data = await fetchVariablesApi();
			setVariablesArray(data.variables_array);
		} catch (error) {
			console.error("fetchVariablesApi failed:", error);
			showToast("Something went wrong with loading variables, please try again.", "danger");
		}
	};

	const handleShowVariableEditor = () => {
		setVariableKey("");
		setShowVariableEditor(true);
	};

	const handleCreateVariable = async () => {
		try {
			await createVariableApi(variableKey);
			showToast("Variable created successfully.", "success");
			fetchVariables();
			handleCloseVariableEditor();
		} catch (error) {
			console.error("createVariableApi failed:", error);
			showToast("" + error, "danger");
		}
	};

	const handleDeleteVariable = async (variable: any) => {
		//ask for confirmation
		const confirmDelete = window.confirm("Are you sure you want to delete this variable? This action cannot be undone.");
		if (!confirmDelete) {
			return;
		}
		try {
			await deleteVariableApi(variable.key);
			showToast("Variable deleted successfully.", "success");
			fetchVariables();
		} catch (error) {
			console.error("deleteVariableApi failed:", error);
			showToast("" + error, "danger");
		}
	};

	const handleDownloadVariables = async (variable: any) => {
		try {
			setLoading(true);
			var response_data = await downloadVariablesApi(variable.key);
			console.log(response_data);
			console.log(response_data.data);
			downloadFile(response_data.data, variable.key + ".csv", "text/csv");
			showToast("Variables downloaded successfully.", "success");
		} catch (error) {
			console.error("downloadVariablesApi failed:", error);
			showToast("" + error, "danger");
		} finally {
			setLoading(false);
		}
	};

	const handleUploadVariables = async (variable: any) => {
		try {
			const input = document.createElement("input");
			input.type = "file";
			input.accept = ".csv";

			input.onchange = async (event: Event) => {
				const target = event.target as HTMLInputElement;
				const file = target.files?.[0];
				if (file) {
					try {
						const reader = new FileReader();
						reader.onload = async (e: ProgressEvent<FileReader>) => {
							try {
								setLoading(true);
								const csvData = e.target?.result as string;
								await uploadVariablesApi(csvData, variable.key);
								showToast("Variables uploaded successfully.", "success");
								fetchVariables();
							} catch (error) {
								console.error("uploadVariablesApi failed:", error);
								showToast("" + error, "danger");
							} finally {
								setLoading(false);
							}
						};

						reader.onerror = (error) => {
							console.error("File reading failed:", error);
							showToast("Failed to read the file.", "danger");
						};
						reader.readAsText(file);
					} catch (error) {
						console.error("uploadVariablesApi failed:", error);
						showToast("" + error, "danger");
					} finally {
						setLoading(false);
					}
				}
			};

			input.click();
		} catch (error) {
			console.error("Error in handleUploadVariables:", error);
			showToast("An unexpected error occurred.", "danger");
		}
	};

	const gridOptions = {
		suppressCellFocus: true,
	};

	useEffect(() => {
		fetchVariables();
	}, [shouldRefresh]);

	const ActionButtons = (params: any) => {
		return (
			<div>
				<Button variant="success" size="sm" onClick={() => handleUploadVariables(params.data)} className="me-3">
					<i className="bi bi-cloud-upload"></i>
				</Button>
				<Button variant="dark" size="sm" onClick={() => handleDownloadVariables(params.data)} className="me-3">
					<i className="bi bi-cloud-download"></i>
				</Button>
				<Button variant="danger" size="sm" onClick={() => handleDeleteVariable(params.data)}>
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

	const viewData = (variable: any) => {
		const key = variable.key;
		navigate("/manage/data-view", { state: { variableKey: key } });
	};

	const columnDefs = [
		{
			headerName: "Variable Key",
			field: "key",
			cellRenderer: (params: any) => <span className="badge badge-primary">{params.value}</span>,
			flex: 3,
			cellStyle: { display: "flex", alignItems: "center" }, // Centering content vertically
		},
		{
			headerName: "Data",
			cellRenderer: (params: any) => (
				<Button variant="outline-secondary" size="sm" onClick={() => viewData(params.data)}>
					View Data
				</Button>
			),
			flex: 1,
			cellStyle: { display: "flex", alignItems: "center" }, // Centering content vertically
		},

		{
			headerName: "Actions",
			cellRenderer: ActionButtons,
			flex: 1,
			cellStyle: { display: "flex", alignItems: "center" }, // Centering content vertically
		},
	];

	return (
		<div className="main-container">
			{loading && (
				<div className="my-3">
					<Spinner animation="border" role="status" variant="success">
						<span className="visually-hidden">Loading...</span>
					</Spinner>
				</div>
			)}

			<div className="mt-3">
				<div className="d-flex justify-content-between align-items-center mb-3 ">
					<h3 className="translucent_white">Variables</h3>
					<div>
						<Button variant="dark" onClick={handleShowVariableEditor}>
							<span className="bi bi-plus-lg"></span>
						</Button>{" "}
					</div>
				</div>
				<div className="ag-theme-custom grid-container">
					<AgGridReact
						rowData={variablesArray}
						columnDefs={columnDefs}
						pagination={true}
						paginationPageSize={10}
						gridOptions={gridOptions}
						defaultColDef={defaultColDef}
					/>
				</div>
			</div>

			<Modal show={showVariableEditor} onHide={handleCloseVariableEditor} size="lg" centered>
				<Modal.Header closeButton>
					<Modal.Title>Create Variable</Modal.Title>
				</Modal.Header>
				<Modal.Body>
					<label htmlFor="variableKey" className="form-label">
						Variable Key
					</label>
					<input type="text" className="form-control" id="variableKey" value={variableKey} onChange={(e) => setVariableKey(e.target.value)} />
					<br></br>
					<div id="projectNameHelp" className="form-text model-text">
						Variable Key must start with project key: <b>{localStorage.getItem("selected_project_key")}</b>
					</div>
					<br></br>

					<Modal.Footer>
						<Button variant="secondary" onClick={handleCloseVariableEditor}>
							Close
						</Button>
						<Button variant="primary" onClick={handleCreateVariable}>
							Create
						</Button>
					</Modal.Footer>
				</Modal.Body>
			</Modal>
		</div>
	);
};

export default VariablesComponent;
