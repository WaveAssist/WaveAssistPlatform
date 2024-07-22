// interface DashboardProps {}

// //Return boilerplate dashboard
// const Dashboard: React.FC<DashboardProps> = () => {
// 	return <div></div>;
// };
// export default Dashboard;

import React, { useEffect, useState, useRef } from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef, GridOptions, GridReadyEvent } from "ag-grid-community";
import "firebase/compat/auth";
import axios from "axios";
import "./dashboard_component.css";
import "../utils/ag-grid-theme-builder.css";
interface DashboardProps {}

const Dashboard: React.FC<DashboardProps> = () => {
	const [dashboardResponseData, setDashboardResponseData] = useState<any>({});
	const [dataFormatArray, setDataFormatArray] = useState<any[]>([]);
	const [dataRefreshPaused, setDataRefreshPaused] = useState(false);
	const gridApiDictionary = useRef<{ [key: string]: any }>({});
	const rowHeight = 25;
	const hiddenKeys = ["id", "row_number"];

	useEffect(() => {
		const fetchData = async () => {
			const url = "https://assistapi.wavepredict.com/load_project_data/";
			const uid = "OFZh5f8n3VZubWJZ4inkqJszXxx1";
			const selectedProjectKey = "Vyapak";
			const selectedFlowId = "1";

			try {
				const response = await axios.post(
					url,
					new URLSearchParams({
						uid,
						project_key: selectedProjectKey,
						flow_id: selectedFlowId,
					}),
					{
						headers: { "Content-Type": "application/x-www-form-urlencoded" },
					}
				);

				if (response.data && !dataRefreshPaused) {
					console.log(response.data.data);
					setDashboardResponseData(response.data.data.data_dict);
					setDataFormatArray(response.data.data.data_format_array);
				}

				setTimeout(fetchData, 50000);
			} catch (error) {
				alert("Something went wrong loading Dashboard Data!");
			}
		};

		fetchData();
	}, [dataRefreshPaused]);

	const getGridOptions = (dataKey: string, editType: string): GridOptions => {
		const keysArray = getKeys(dataKey);
		const columnDefsArray: ColDef[] = keysArray.map((key) => {
			const len = key.split(" ").reduce((a, b) => (a.length > b.length ? a : b)).length;
			return {
				field: key,
				width: len * 3,
				hide: hiddenKeys.includes(key),
			};
		});

		const shouldEdit = editType === "1";

		return {
			columnDefs: columnDefsArray,
			pagination: true,
			paginationPageSize: 20,
			rowSelection: "multiple",
			animateRows: true,
			domLayout: "autoHeight",
			headerHeight: 60,
			suppressPropertyNamesCheck: true,
			defaultColDef: {
				sortable: true,
				filter: true,
				resizable: true,
				autoHeight: true,
				wrapHeaderText: true,
				autoHeaderHeight: true,
				editable: shouldEdit,
				enableCellChangeFlash: true,
				cellDataType: false,
				minWidth: 50,
				onCellValueChanged: (event) => onCellValueChanged(dataKey, event),
			},
			onRowClicked: (_event: any) => console.log("A row was clicked"),
			onColumnResized: (_event: any) => console.log("A column was resized"),
			getRowId: (params) => params.data.row_number,
			getRowHeight: () => rowHeight,
		};
	};

	const onCellValueChanged = (dataKey: string, event: any) => {
		const updatedDataDict = event.data;
		if (updatedDataDict.hasOwnProperty("row_number")) {
			const rowNumber = updatedDataDict["row_number"];
			const originalDataArray = dashboardResponseData[dataKey];

			const updatedDataArray = originalDataArray.map((item: any) => (item["row_number"] === rowNumber ? updatedDataDict : item));

			updateData(dataKey, updatedDataArray);
		} else if (isRowDataCompleted(dataKey, updatedDataDict)) {
			const originalDataArray = dashboardResponseData[dataKey];
			originalDataArray.push(updatedDataDict);
			setDataRefreshPaused(false);
			updateData(dataKey, originalDataArray);
		}
	};

	const isRowDataCompleted = (dataKey: string, dataDict: any): boolean => {
		const keysArray = getKeysWithoutID(dataKey);
		return keysArray.every((key) => dataDict[key] != null);
	};

	const updateData = async (dataKey: string, dataDict: any) => {
		const url = "https://assistapi.wavepredict.com/set_data_for_key/";
		const uid = localStorage.getItem("uid") || "";
		const jwtToken = localStorage.getItem("jwt_token") || "";
		const selectedProjectKey = localStorage.getItem("selected_project_key") || "";
		const selectedFlowId = localStorage.getItem("selected_flow_id") || "";

		try {
			const response = await axios.post(
				url,
				new URLSearchParams({
					jwt_token: jwtToken,
					uid,
					project_key: selectedProjectKey,
					io_data_key: dataKey,
					flow_id: selectedFlowId,
					json_data: JSON.stringify(dataDict),
					data_type: "json",
				}),
				{
					headers: { "Content-Type": "application/x-www-form-urlencoded" },
				}
			);

			if (response.data) {
				console.log("Value Updated Successfully!");
			} else {
				alert("Something went wrong with updating data. Please try again.");
			}
		} catch (error) {
			console.error(error);
		}
	};

	const addRow = (dataKey: string) => {
		const gridApi = gridApiDictionary.current[dataKey];
		setDataRefreshPaused(true);
		gridApi.applyTransaction({ add: [{}] });
	};

	const onGridReady = (params: GridReadyEvent, dataKey: string) => {
		const gridApi = params.api;
		gridApiDictionary.current[dataKey] = gridApi;
		gridApi.sizeColumnsToFit();
	};

	const getKeys = (dataKey: string): string[] => {
		const dataArray = dashboardResponseData[dataKey];
		return dataArray && dataArray.length > 0 ? Object.keys(dataArray[0]) : [];
	};

	const getKeysWithoutID = (dataKey: string): string[] => {
		const dataArray = dashboardResponseData[dataKey];
		const keys = dataArray && dataArray.length > 0 ? Object.keys(dataArray[0]) : [];
		return keys.filter((key) => !hiddenKeys.includes(key));
	};

	const getFirstValueForKey = (dataKey: string, dictKey: string): string => {
		const dataArray = dashboardResponseData[dataKey];
		return dataArray && dataArray.length > 0 ? dataArray[0][dictKey] : "";
	};

	const getRows = (): any[] => {
		const rows = dataFormatArray.map((item) => item.Row);
		return [...new Set(rows)];
	};

	const getArrayForRow = (rowValue: string): any[] => {
		return dataFormatArray.filter((item) => item.Row === rowValue);
	};

	const getBootstrapClasses = (item: any): string[] => {
		const rowCount = dataFormatArray.filter((formatDict) => formatDict.Row === item.Row).length;
		const colValue = 12 / rowCount;
		const colClass = `col-md-${Math.floor(colValue)}`;
		return [colClass, "col-class", item.Column === 1 ? "col-class-first" : ""].filter(Boolean);
	};

	return (
		<div className="base_component">
			{getRows().map((rowNumber) => (
				<div className="row" key={rowNumber}>
					{getArrayForRow(rowNumber).map((item) => (
						<div key={item.id} className={getBootstrapClasses(item).join(" ")}>
							{item.Title_Type === 1 && (
								<h2 className="data-title">
									{item.Title}
									{item.Edit_Type === 1 && (
										<button className="btn btn-outline-secondary add_button" onClick={() => addRow(item.Data_Key)}>
											+
										</button>
									)}
								</h2>
							)}

							{item.Type === "Table" && (
								<div className="ag-theme-custom grid-container ag-grid-table">
									<AgGridReact
										gridOptions={getGridOptions(item.Data_Key, item.Edit_Type.toString())}
										onGridReady={(params) => onGridReady(params, item.Data_Key)}
										rowData={dashboardResponseData[item.Data_Key]}
									/>
								</div>
							)}

							{item.Type === "Numbers" && (
								<div className="row data-row">
									{getKeysWithoutID(item.Data_Key).map((key) => (
										<div className="col data-col" key={key}>
											<h4 className="data-title">{key}</h4>
											<p className="data-value">{getFirstValueForKey(item.Data_Key, key)}</p>
										</div>
									))}
								</div>
							)}
						</div>
					))}
					<div className="separator"></div>
				</div>
			))}
		</div>
	);
};

export default Dashboard;
