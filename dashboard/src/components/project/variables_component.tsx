import React, { useEffect, useState, useRef } from "react";
import { fetchVariablesApi, fetchDataForKeyAPI, createVariableApi, setDataForKeyApi } from "../../services/project_services";
import { useToast } from "../../utils/toast_context";
import { Form, Button, Spinner, DropdownButton, Dropdown } from "react-bootstrap";
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
			const rowData = flatKeys.map((variable: any) => ({
				key: variable, // Auto-generate a variable key like "Var1", "Var2", etc.
				value: variable, // Use the actual variable value
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

	// const handleDeleteVariable = async (variable: any) => {
	// 	//ask for confirmation
	// 	const confirmDelete = window.confirm("Are you sure you want to delete this variable? This action cannot be undone.");
	// 	if (!confirmDelete) {
	// 		return;
	// 	}
	// 	try {
	// 		await deleteVariableApi(variable.key);
	// 		showToast("Variable deleted successfully.", "success");
	// 		fetchVariables();
	// 	} catch (error) {
	// 		console.error("deleteVariableApi failed:", error);
	// 		showToast("" + error, "danger");
	// 	}
	// };

	// const handleDownloadVariables = async (variable: any) => {
	// 	try {
	// 		setLoading(true);
	// 		var response_data = await downloadVariablesApi(variable.key);
	// 		downloadFile(response_data.data, variable.key + ".json", "text/json");
	// 		showToast("Variables downloaded successfully.", "success");
	// 	} catch (error) {
	// 		console.error("downloadVariablesApi failed:", error);
	// 		showToast("" + error, "danger");
	// 	} finally {
	// 		setLoading(false);
	// 	}
	// };

	// const handleUploadVariables = async (variable: any) => {
	// 	try {
	// 		const input = document.createElement("input");
	// 		input.type = "file";
	// 		input.accept = ".csv";

	// 		input.onchange = async (event: Event) => {
	// 			const target = event.target as HTMLInputElement;
	// 			const file = target.files?.[0];
	// 			if (file) {
	// 				try {
	// 					const reader = new FileReader();
	// 					reader.onload = async (e: ProgressEvent<FileReader>) => {
	// 						try {
	// 							setLoading(true);
	// 							const csvData = e.target?.result as string;
	// 							await uploadVariablesApi(csvData, variable.key);
	// 							showToast("Variables uploaded successfully.", "success");
	// 							fetchVariables();
	// 						} catch (error) {
	// 							console.error("uploadVariablesApi failed:", error);
	// 							showToast("" + error, "danger");
	// 						} finally {
	// 							setLoading(false);
	// 						}
	// 					};

	// 					reader.onerror = (error) => {
	// 						console.error("File reading failed:", error);
	// 						showToast("Failed to read the file.", "danger");
	// 					};
	// 					reader.readAsText(file);
	// 				} catch (error) {
	// 					console.error("uploadVariablesApi failed:", error);
	// 					showToast("" + error, "danger");
	// 				} finally {
	// 					setLoading(false);
	// 				}
	// 			}
	// 		};

	// 		input.click();
	// 	} catch (error) {
	// 		console.error("Error in handleUploadVariables:", error);
	// 		showToast("An unexpected error occurred.", "danger");
	// 	}
	// };

	const gridOptions = {
		suppressCellFocus: true,
	};

	useEffect(() => {
		fetchVariables();
	}, [shouldRefresh]);

	// const ActionButtons = (params: any) => {
	// 	return (
	// 		<div>
	// 			<Button variant="success" size="sm" onClick={() => handleUploadVariables(params.data)} className="me-3">
	// 				<i className="bi bi-cloud-upload"></i>
	// 			</Button>
	// 			<Button variant="dark" size="sm" onClick={() => handleDownloadVariables(params.data)} className="me-3">
	// 				<i className="bi bi-cloud-download"></i>
	// 			</Button>
	// 			<Button variant="danger" size="sm" onClick={() => handleDeleteVariable(params.data)}>
	// 				<i className="bi bi-trash"></i>
	// 			</Button>
	// 		</div>
	// 	);
	// };

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
			if (dataType == "dataframe") {
				setDataForDataframe(displayData);
			} else if (dataType == "json") {
				setJsonDataString(JSON.stringify(displayData, null, 2));
			} else if (dataType == "string") {
				setStringData(displayData);
			}
			setLoading(false); // Hide loader after fetch
		} catch (error) {
			console.error("fetchDataForKeyAPI failed:", error);
			showToast("Something went wrong with loading data, please try again.", "danger");
			setLoading(false); // Hide loader even if fetch fails
		}
	};

	const viewData = async (variable: any) => {
		const key = variable.key;
		setSelectedVariableKey(key);
		setLoading(true);
		await fetchDataForKey(key);
		setLoading(false);
		setShowDataViewer(true);
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
				<Button variant="outline-secondary" size="sm" onClick={() => viewData(params.data)}>
					View Data
				</Button>
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
