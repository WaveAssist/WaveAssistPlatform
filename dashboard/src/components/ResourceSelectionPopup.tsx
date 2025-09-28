import React, { useState, useCallback } from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef, GridReadyEvent, SelectionChangedEvent, RowClickedEvent } from "ag-grid-community";
import "./ResourceSelectionPopup.css";

interface Resource {
	id: string;
	name: string;
	extra?: any;
}

interface ResourceSelectionPopupProps {
	isOpen: boolean;
	onClose: () => void;
	resources: Resource[];
	onSave: (selectedResources: Resource[]) => void;
	providerName: string;
}

const ResourceSelectionPopup: React.FC<ResourceSelectionPopupProps> = ({ isOpen, onClose, resources, onSave, providerName }) => {
	const [selectedResources, setSelectedResources] = useState<Resource[]>([]);

	const columnDefs: ColDef[] = [
		{
			headerName: "Select",
			field: "select",
			checkboxSelection: true,
			headerCheckboxSelection: true,
			width: 80,
			pinned: "left",
		},
		{
			headerName: "ID",
			field: "id",
			width: 200,
			sortable: true,
			filter: true,
		},
		{
			headerName: "Name",
			field: "name",
			width: 300,
			sortable: true,
			filter: true,
		},
	];

	const defaultColDef: ColDef = {
		resizable: true,
		sortable: true,
		filter: true,
		minWidth: 150,
		cellStyle: { display: "flex", alignItems: "center" },
	};

	const onGridReady = useCallback((params: GridReadyEvent) => {
		params.api.sizeColumnsToFit();
	}, []);

	const onSelectionChanged = useCallback((event: SelectionChangedEvent) => {
		const selectedNodes = event.api.getSelectedNodes();
		const selectedData = selectedNodes.map((node) => node.data);
		setSelectedResources(selectedData);
	}, []);

	const onRowClicked = useCallback((event: RowClickedEvent) => {
		const node = event.node;
		const isSelected = node.isSelected();

		// Toggle selection for this row
		node.setSelected(!isSelected);
	}, []);

	const handleSave = () => {
		console.log("Selected resources:", selectedResources);
		onSave(selectedResources);
		onClose();
	};

	const handleClose = () => {
		setSelectedResources([]);
		onClose();
	};

	if (!isOpen) return null;

	return (
		<div className="resource-popup-overlay">
			<div className="resource-popup-container">
				<div className="resource-popup-header">
					<h4>Select {providerName} Resources</h4>
					<button type="button" className="btn-close" onClick={handleClose} aria-label="Close">
						×
					</button>
				</div>

				<div className="resource-popup-body">
					<div className="ag-theme-balham-dark resource-grid">
						<AgGridReact
							rowData={resources}
							columnDefs={columnDefs}
							defaultColDef={defaultColDef}
							rowSelection="multiple"
							onGridReady={onGridReady}
							onSelectionChanged={onSelectionChanged}
							onRowClicked={onRowClicked}
							suppressRowClickSelection={true}
							animateRows={true}
							pagination={true}
							paginationPageSize={20}
							domLayout="autoHeight"
							headerHeight={50}
							rowHeight={40}
						/>
					</div>
				</div>

				<div className="resource-popup-footer">
					<div className="selected-count">{selectedResources.length} resource(s) selected</div>
					<div className="popup-actions">
						<button type="button" className="btn btn-secondary" onClick={handleClose}>
							Cancel
						</button>
						<button type="button" className="btn btn-primary" onClick={handleSave} disabled={selectedResources.length === 0}>
							Save Selection
						</button>
					</div>
				</div>
			</div>
		</div>
	);
};

export default ResourceSelectionPopup;
