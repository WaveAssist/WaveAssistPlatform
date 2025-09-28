import React, { useState, useCallback } from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef, SelectionChangedEvent } from "ag-grid-community";
import Modal from "react-bootstrap/Modal";
import { Button } from "react-bootstrap";
import "./ResourceSelectionPopup.css";
import "../utils/ag-theme-project.css";

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
			headerName: "All",
			field: "select",
			checkboxSelection: true,
			headerCheckboxSelection: true,
			width: 80,
			pinned: "left",
			sortable: false,
			filter: false,
			resizable: false,
			suppressSizeToFit: true,
		},
		{
			headerName: "ID",
			field: "id",
			width: 350,
			sortable: true,
			filter: true,
			resizable: false,
			suppressSizeToFit: true,
		},
		{
			headerName: "Name",
			field: "name",
			width: 400,
			sortable: true,
			filter: false,
			resizable: false,
			suppressSizeToFit: true,
		},
	];

	const gridOptions = {
		suppressCellFocus: true,
	};

	const defaultColDef = {
		autoHeight: true,
		wrapText: true,
		enableCellChangeFlash: true,
		editable: false,
		cellClass: "ag-cell",
	};

	const onGridReady = useCallback(() => {
		// Grid is ready with fixed column widths
	}, []);

	const onSelectionChanged = useCallback((event: SelectionChangedEvent) => {
		const selectedNodes = event.api.getSelectedNodes();
		const selectedData = selectedNodes.map((node) => node.data);
		setSelectedResources(selectedData);
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

	return (
		<Modal show={isOpen} onHide={handleClose} size="lg" centered>
			<Modal.Header closeButton>
				<Modal.Title>Select {providerName} Resources</Modal.Title>
			</Modal.Header>
			<Modal.Body style={{ height: "400px", padding: "0" }}>
				<div className="ag-theme-custom grid-container" style={{ flex: 1 }}>
					<AgGridReact
						rowData={resources}
						columnDefs={columnDefs}
						gridOptions={gridOptions}
						defaultColDef={defaultColDef}
						rowSelection="multiple"
						onGridReady={onGridReady}
						onSelectionChanged={onSelectionChanged}
						suppressRowClickSelection={true}
						pagination={true}
						paginationPageSize={10}
					/>
				</div>
			</Modal.Body>
			<Modal.Footer>
				<div className="d-flex justify-content-between align-items-center w-100">
					<div className="selected-count text-muted">{selectedResources.length} resource(s) selected</div>
					<div className="d-flex gap-2">
						<Button variant="secondary" onClick={handleClose}>
							Cancel
						</Button>
						<Button variant="primary" onClick={handleSave} disabled={selectedResources.length === 0}>
							Save Selection
						</Button>
					</div>
				</div>
			</Modal.Footer>
		</Modal>
	);
};

export default ResourceSelectionPopup;
