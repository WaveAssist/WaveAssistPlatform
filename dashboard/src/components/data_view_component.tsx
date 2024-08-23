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

const DataViewComponent: React.FC = () => {
	const [dataArray, setDataArray] = useState<any[]>([]);
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
			const variableKeys = data.variables_array.map((variable: any) => variable.key);
			setVariablesArray(variableKeys);

			const firstVariableKey = variableKeys[0];
			setSelectedVariableKey(variableKey || firstVariableKey);
		} catch (error) {
			console.error("fetchVariablesApi failed:", error);
			showToast("Something went wrong with loading variables, please try again.", "danger");
		}
	};

	const fetchDataForKey = async (data_key: string) => {
		try {
			const data = await fetchDataForKeyAPI(data_key);
			setDataArray(data[data_key]);

			if (data[data_key].length > 0) {
				const keys = Object.keys(data[data_key][0]);
				const newColumnDefs = keys.map((key) => ({
					field: key,
					sortable: true,
					filter: true,
					resizable: true,
					autoHeaderHeight: true,
				}));
				setColumnDefs(newColumnDefs);
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

			const intervalId = setInterval(() => {
				fetchDataForKey(selectedVariableKey);
			}, 10000);

			// Clean up the interval on component unmount or when selectedVariableKey changes
			return () => clearInterval(intervalId);
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
				<div className="ag-theme-balham-dark grid-container full-screen">
					<AgGridReact
						columnDefs={columnDefs}
						rowData={dataArray}
						pagination={true}
						paginationPageSize={20}
						animateRows={true}
						domLayout="autoHeight"
						headerHeight={50} // Set the header height to 80px
						defaultColDef={{
							sortable: true,
							filter: true,
							resizable: true,
							cellStyle: { display: "flex", alignItems: "center" }, // Center content vertically
						}}
						onGridReady={(params) => params.api.sizeColumnsToFit()}
					/>
				</div>
			)}
		</div>
	);
};

export default DataViewComponent;
