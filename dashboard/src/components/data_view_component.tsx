import React, { useEffect, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef } from "ag-grid-community";
import "./data_view_component.css";
import "ag-grid-community/styles/ag-theme-balham.css";
import { fetchDataForKeyAPI, fetchVariablesApi } from "../services/project_services";
import { useToast } from "../utils/toast_context";
import DarkDropdown from "../utils/dark_dropdown";
import { useRefresh } from "../utils/RefreshContext";
import { Spinner } from "react-bootstrap"; // Assuming you're using Bootstrap
import { useLocation } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { Form } from "react-bootstrap";

const DataViewComponent: React.FC = () => {
	const [dataArray, setDataArray] = useState<any[]>([]);
	const [jsonDataString, setJsonDataString] = useState<string>("");
	const [stringData, setStringData] = useState<string>("");
	const [dataType, setDataType] = useState<string | undefined>(undefined);
	const [columnDefs, setColumnDefs] = useState<ColDef[]>([]);
	const [selectedVariableKey, setSelectedVariableKey] = useState<string | undefined>(undefined);
	const [variablesArray, setVariablesArray] = useState<string[]>([]);
	const [loading, setLoading] = useState<boolean>(true);
	const { showToast } = useToast();
	const { shouldRefresh } = useRefresh();
	const location = useLocation();
	const { variableKey } = location.state || {};

	const fetchVariables = async () => {
		try {
			const data = await fetchVariablesApi();
			const variableKeys = data.data_keys;
			setVariablesArray(variableKeys);

			const firstVariableKey = variableKeys[0];
			setSelectedVariableKey(variableKey || firstVariableKey);
		} catch (error) {
			console.error("fetchVariablesApi failed:", error);
			showToast("Something went wrong with loading variables, please try again.", "danger");
		}
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

	const fetchDataForKey = async (data_key: string) => {
		try {
			const data = await fetchDataForKeyAPI(data_key);
			const displayData = data.data;
			const dataType = data.data_type;
			setDataType(dataType);
			if (dataType == "dataframe") {
				if (displayData.length > 0) {
					setDataArray(displayData);
					const keys = Object.keys(displayData[0]);
					const newColumnDefs = keys.map((key) => ({
						field: key,
						sortable: true,
						filter: true,
						resizable: true,
						autoHeaderHeight: true,
					}));
					setColumnDefs(newColumnDefs);
				}
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

	useEffect(() => {
		fetchVariables();
	}, [shouldRefresh]);

	useEffect(() => {
		if (selectedVariableKey) {
			setLoading(true); // Show loader whenever selectedVariableKey changes
			fetchDataForKey(selectedVariableKey);
		}
	}, [selectedVariableKey]);

	const handleVariableSelect = (key: string) => {
		setSelectedVariableKey(key);
	};

	return (
		<div className="data-viewer-container">
			<div className="header d-flex justify-content-between align-items-center mb-4">
				<h3 className="translucent_white">Data Viewer</h3>
				<DarkDropdown
					items={variablesArray}
					keys={variablesArray}
					defaultText={selectedVariableKey || "Select Variable"}
					headerText="Select Variable"
					onItemSelect={handleVariableSelect}
				/>
			</div>

			{loading ? (
				<div className="loader-container d-flex justify-content-center align-items-center">
					<Spinner animation="border" role="status" variant="success">
						<span className="visually-hidden">Loading...</span>
					</Spinner>
				</div>
			) : (
				<div className="content-container">
					{dataType === "dataframe" && (
						<div className="ag-theme-balham-dark grid-container full-screen">
							<AgGridReact
								columnDefs={columnDefs}
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
									minWidth: 150,
									cellStyle: { display: "flex", alignItems: "center" },
								}}
								onGridReady={(params) => params.api.sizeColumnsToFit()}
							/>
						</div>
					)}
					{dataType === "string" && (
						<div className="string-container">
							<Form>
								<div className="d-flex align-items-center gap-2 mb-3">
									<Form.Label className="mb-0 text-white">{selectedVariableKey}:</Form.Label>
									<Form.Control type="text" className="w-50" value={stringData} /> {/*onChange={(e) => setStringData(e.target.value)} */}
									{/* <Button type="submit" variant="primary">
										Update
									</Button> */}
								</div>
							</Form>
						</div>
					)}
					{dataType === "json" && (
						<div className="json-container">
							<Editor width="100%" height="500px" theme="vs-dark" defaultLanguage="json" value={jsonDataString} options={editorOptions} />
						</div>
					)}
				</div>
			)}
		</div>
	);
};

export default DataViewComponent;
