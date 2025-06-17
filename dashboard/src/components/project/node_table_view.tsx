import { AgGridReact } from "ag-grid-react";
import { GridOptions } from "ag-grid-community";
import "../../utils/ag-theme-project.css";
import "./project_components.css";

type Props = {
	rowData: any[];
	columnDefs: any[];
	gridOptions?: GridOptions;
	defaultColDef?: any;
};

export default function NodeTableView({ rowData, columnDefs, gridOptions, defaultColDef }: Props) {
	return (
		<div className="ag-theme-custom grid-container">
			<AgGridReact
				rowData={rowData}
				columnDefs={columnDefs}
				gridOptions={gridOptions}
				pagination={true}
				paginationPageSize={10}
				defaultColDef={defaultColDef}
			/>
		</div>
	);
}
