import React, { useEffect, useState, useRef } from "react";
import { fetchVariablesApi, fetchDataForKeyAPI, createVariableApi, setDataForKeyApi } from "../../services/project_services";
import { useToast } from "../../utils/toast_context";
import { Form, Button, Spinner, DropdownButton, Dropdown } from "react-bootstrap";
import Papa from 'papaparse';
import { AgGridReact } from "ag-grid-react"; // for JSX
import type { AgGridReact as AgGridReactType } from "ag-grid-react"; // for typing
import "./project_components.css";
import "../../utils/ag-theme-project.css";
import Modal from "react-bootstrap/Modal";
import { useRefresh } from "../../utils/RefreshContext";
import Editor from "@monaco-editor/react";
import { ColDef } from "ag-grid-community";

const VariablesComponent: React.FC = () => {
	const [variablesArray, setVariablesArray] = useState<any[]>([]);
	const [newDataType, setNewDataType] = useState<string>("json");
	const { showToast } = useToast();
	const [dataColumnDefs, setDataColumnDefs] = useState<ColDef[]>([]);
	const [showVariableEditor, setShowVariableEditor] = useState(false);
	const [loading, setLoading] = useState(false);
	const [dataArray, setDataArray] = useState<any[]>([]);
	const [jsonDataString, setJsonDataString] = useState<string>("");
	const [stringData, setStringData] = useState<string>("");
	const [dataType, setDataType] = useState<string | undefined>(undefined);
	const [showDataViewer, setShowDataViewer] = useState(false);
	const [selectedVariableKey, setSelectedVariableKey] = useState<string | undefined>(undefined);
	const [variableKey, setVariableKey] = useState("");
	const { shouldRefresh } = useRefresh();
	const gridRef = useRef<AgGridReactType | null>(null);

	const handleCloseVariableEditor = () => {
		setShowVariableEditor(false);
	};

	const handleSaveDataChanges = async () => {
		try {
			var updatedData: any = "";
			if (dataType === "json") {
				try {
					updatedData = JSON.parse(jsonDataString);
				} catch (error) {
					console.error("Error parsing JSON data:", error);
					showToast("Invalid JSON format. Please correct it and try again.", "danger");
					return;
				}
			} else if (dataType === "string") {
				updatedData = typeof stringData === "string" ? stringData : String(stringData);
			} else if (dataType === "dataframe") {
				updatedData = getEditedDataArray();
			}
			showToast("Data saved successfully.", "success");
			try {
				await setDataForKeyApi(updatedData, selectedVariableKey!, dataType!);
			} catch (error) {
				console.error("Error in setDataForKeyApi:", error);
				showToast("Failed to save data to the server.", "danger");
			}
			setShowDataViewer(false);
		} catch (error) {
			console.error("Error saving data:", error);
			showToast("Failed to save data.", "danger");
		}
	};

	const handleCloseDataViewer = () => {
		setShowDataViewer(false);
	};
	const fetchVariables = async () => {
		setLoading(true);
		try {
			const data = await fetchVariablesApi();
			var flatKeys = data.data_keys;
			const rowData = await Promise.all(flatKeys.map(async (variable: any) => {
				try {
					const varData = await fetchDataForKeyAPI(variable);
					return {
						key: variable,
						value: variable,
						dataType: varData.data_type
					};
				} catch (error) {
					return {
						key: variable,
						value: variable,
						dataType: null
					};
				}
			}));

			setVariablesArray(rowData);
		} catch (error) {
			console.error("fetchVariablesApi failed:", error);
			showToast("Something went wrong with loading variables, please try again.", "danger");
		}
		setLoading(false);
	};

	const handleShowVariableEditor = () => {
		setVariableKey("");
		setShowVariableEditor(true);
	};

	const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>, variableKey: string) => {
		const file = event.target.files?.[0];
		if (!file) return;

		// Check if file is a CSV
		if (!file.name.toLowerCase().endsWith('.csv')) {
			showToast('Please upload only CSV files', 'danger');
			// Reset the file input
			event.target.value = '';
			return;
		}

		setLoading(true); // Start loading
		try {
			const result = await new Promise((resolve, reject) => {
				Papa.parse(file, {
					complete: resolve,
					error: reject,
					header: true,
				});
			});

			const parsedData = (result as any).data;
			await setDataForKeyApi(parsedData, variableKey, 'dataframe');
			showToast('CSV file uploaded successfully', 'success');
			fetchDataForKey(variableKey);
		} catch (error) {
			console.error('Error uploading CSV:', error);
			showToast('Error uploading CSV file', 'danger');
		} finally {
			setLoading(false); // Stop loading regardless of success or failure
			// Reset the file input
			event.target.value = '';
		}
	};

	const handleCreateVariable = async () => {
		try {
			await createVariableApi(variableKey, newDataType);
			showToast("Variable created successfully.", "success");
			fetchVariables();
			handleCloseVariableEditor();
		} catch (error) {
			console.error("createVariableApi failed:", error);
			showToast("" + error, "danger");
		}
	};

	const gridOptions = {
		suppressCellFocus: true,
	};

	useEffect(() => {
		fetchVariables();
	}, [shouldRefresh]);

	const getEditedDataArray = () => {
		const updatedData: any[] = [];

		gridRef.current?.api.forEachNode((node) => {
			updatedData.push({ ...node.data }); // clone to keep structure intact
		});

		return updatedData;
	};

	const defaultColDef = {
		autoHeight: true,
		wrapText: true,
		enableCellChangeFlash: true,
		editable: false,
		cellClass: "ag-cell",
		sortable: true,
		filter: true,
	};

	const editorOptions = {
		selectOnLineNumbers: true,
		roundedSelection: false,
		readOnly: false,
		automaticLayout: true,
		language: "json", // Set the language to Python for syntax highlighting
		theme: "vs-dark", // Use a dark theme
		mode: "json",
		quickSuggestions: true, // Enable quick suggestions
	};

	const setDataForDataframe = (displayData: any) => {
		if (displayData.length > 0) {
			setDataArray(displayData);
			const keys = Object.keys(displayData[0]);
			const newColumnDefs = keys.map((key) => ({
				field: key,
				sortable: true,
				filter: true,
				resizable: true,
				autoHeaderHeight: true,
				editable: true,
			}));
			setDataColumnDefs(newColumnDefs);
		}
	};

	const fetchDataForKey = async (data_key: string) => {
		try {
			const data = await fetchDataForKeyAPI(data_key);
			const displayData = data.data;
			const dataType = data.data_type;
			setDataType(dataType);

			if (dataType === "dataframe") {
				setDataForDataframe(displayData);
			} else if (dataType === "json") {
				setJsonDataString(JSON.stringify(displayData, null, 2));
			} else if (dataType === "string") {
				setStringData(displayData);
			}
		} catch (error: any) {
			console.error("fetchDataForKeyAPI failed:", error);
			const errMsg = error?.message || error?.toString();
			if (errMsg.includes("Data not found")) {
				showToast("No data found for this variable.", "danger");
			} else {
				showToast("Something went wrong with loading data, please try again.", "danger");
			}
			return false;
		} finally {
			setLoading(false); // Always hide loader
		}
		return true;
	};

	const viewData = async (variable: any) => {
		const key = variable.key;
		setSelectedVariableKey(key);
		setJsonDataString("");
		setStringData("");
		setLoading(true);
		var success = await fetchDataForKey(key); // `fetchDataForKey` handles loader off
		if (success) {
			setShowDataViewer(true);
		}
	};

	const columnDefs = [
		{
			headerName: "Variable Key",
			field: "value",
			cellRenderer: (params: any) => <span className="badge badge-primary">{params.value}</span>,
			flex: 3,
			cellStyle: { display: "flex", alignItems: "center" }, // Centering content vertically
		},
		{
			headerName: "Data",
			cellRenderer: (params: any) => (
				<div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
					<Button 
						variant="outline-success" 
						size="sm" 
						className="d-flex align-items-center gap-2"
						onClick={() => viewData(params.data)}
					>
						View Data
					</Button>
					{params.data.dataType === 'dataframe' && (
						<div className="file-upload-container">
							<input
								type="file"
								accept=".csv"
								onChange={(e) => handleFileUpload(e, params.data.key)}
								style={{ display: 'none' }}
								id={`file-upload-${params.data.key}`}
							/>
							<Button
								variant="outline-success"
								size="sm"
								className="d-flex align-items-center"
								onClick={() => document.getElementById(`file-upload-${params.data.key}`)?.click()}
								title="Upload CSV"
							>
								<i className="bi bi-cloud-upload me-2"></i>
								 Upload
							</Button>
						</div>
					)}
				</div>
			),
			flex: 1,
			cellStyle: { display: "flex", alignItems: "center" }, // Centering content vertically
		},

		// {
		// 	headerName: "Actions",
		// 	cellRenderer: ActionButtons,
		// 	flex: 1,
		// 	cellStyle: { display: "flex", alignItems: "center" }, // Centering content vertically
		// },
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

					<hr />
					{/* Schedule Type */}
					<Form.Label>Data Type: </Form.Label>
					<Form.Group controlId="data_type">
						<DropdownButton variant="secondary" title={newDataType} id="scheduleTypeDropdown" onSelect={(selected) => setNewDataType(selected!)}>
							<Dropdown.Item eventKey="json">json</Dropdown.Item>
							<Dropdown.Item eventKey="string">string</Dropdown.Item>
							<Dropdown.Item eventKey="dataframe">dataframe</Dropdown.Item>
						</DropdownButton>
					</Form.Group>
					<br></br>
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

			<Modal show={showDataViewer} onHide={handleCloseDataViewer} size="lg" centered>
				<Modal.Header closeButton>
					<Modal.Title>Data Viewer</Modal.Title>
				</Modal.Header>
				<Modal.Body>
					<Form>
						<div className="content-container">
							{dataType === "dataframe" && (
								<div className="ag-theme-balham-dark">
									<AgGridReact
										ref={gridRef}
										columnDefs={dataColumnDefs}
										rowData={dataArray}
										pagination={true}
										paginationPageSize={20}
										animateRows={true}
										domLayout="autoHeight"
										headerHeight={50}
										defaultColDef={{
											sortable: true,
											filter: true,
											resizable: true,
											cellStyle: { display: "flex", alignItems: "center" },
										}}
										onGridReady={(params) => params.api.sizeColumnsToFit()}
									/>
								</div>
							)}
							{dataType === "string" && (
								<div className="string-container">
									<div className="d-flex align-items-center gap-2 mb-3">
										<Form.Label className="mb-0 text-white">{selectedVariableKey}:</Form.Label>
										<Form.Control type="text" className="w-50" value={stringData} onChange={(e) => setStringData(e.target.value)} />
									</div>
								</div>
							)}
							{dataType === "json" && (
								<div className="json-container">
									<Editor
										width="100%"
										height="500px"
										theme="vs-dark"
										defaultLanguage="json"
										value={jsonDataString}
										options={editorOptions}
										onChange={(newValue: any) => setJsonDataString(newValue)}
									/>
								</div>
							)}
						</div>
						{/* Modal Footer */}
						<Modal.Footer>
							{dataType === "dataframe" && (
								<Button variant="dark" onClick={() => gridRef.current?.api.exportDataAsCsv()}>
									<i className="bi bi-cloud-download"></i>
								</Button>
							)}
							<Button variant="secondary" onClick={handleCloseDataViewer}>
								Close
							</Button>
							<Button variant="primary" onClick={handleSaveDataChanges}>
								Save
							</Button>
						</Modal.Footer>
					</Form>
				</Modal.Body>
			</Modal>
		</div>
	);
};

export default VariablesComponent;
