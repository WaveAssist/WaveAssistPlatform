import React, { useState, useCallback, useEffect } from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef, SelectionChangedEvent, ICellRendererParams } from "ag-grid-community";
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
	isDismissable?: boolean;
	initiallySelectedResources?: Resource[];
}

// Custom cell renderer for the select button
const SelectButtonRenderer: React.FC<ICellRendererParams> = (params) => {
	const isSelected = params.node.isSelected();

	const handleClick = () => {
		params.node.setSelected(!isSelected);
		params.api.refreshCells({ rowNodes: [params.node], force: true });
	};

	return (
		<Button
			variant={isSelected ? "primary" : "outline-secondary"}
			size="sm"
			onClick={handleClick}
			style={{
				width: "100%",
				fontSize: "12px",
				padding: "4px 8px",
			}}>
			{isSelected ? "Selected" : "Select"}
		</Button>
	);
};

const ResourceSelectionPopup: React.FC<ResourceSelectionPopupProps> = ({
	isOpen,
	onClose,
	resources,
	onSave,
	providerName,
	isDismissable = true,
	initiallySelectedResources = [],
}) => {
	const [selectedResources, setSelectedResources] = useState<Resource[]>(initiallySelectedResources);

	// Update selected resources when popup opens with different initial selections
	useEffect(() => {
		if (isOpen) {
			setSelectedResources(initiallySelectedResources);
		}
	}, [isOpen, initiallySelectedResources]);

	const columnDefs: ColDef[] = [
		{
			headerName: "Resource",
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
			width: 300,
			sortable: true,
			filter: false,
			resizable: false,
			suppressSizeToFit: true,
		},
		{
			headerName: "Select",
			field: "select",
			cellRenderer: SelectButtonRenderer,
			width: 160,
			sortable: false,
			pinned: "right",
			filter: false,
			resizable: false,
			suppressSizeToFit: true,
		},
	];

	const gridOptions = {
		suppressCellFocus: true,
		rowHeight: 50,
	};

	const defaultColDef = {
		autoHeight: false,
		wrapText: true,
		enableCellChangeFlash: true,
		editable: false,
		cellClass: "ag-cell",
	};

	const onGridReady = useCallback(
		(params: any) => {
			// Preselect initially selected resources
			if (initiallySelectedResources && initiallySelectedResources.length > 0) {
				const selectedIds = initiallySelectedResources.map((resource) => resource.id);
				params.api.forEachNode((node: any) => {
					if (selectedIds.includes(node.data.id)) {
						node.setSelected(true);
					}
				});
			}
		},
		[initiallySelectedResources]
	);

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
		<Modal show={isOpen} onHide={handleClose} size="lg" centered backdrop="static">
			<Modal.Header closeButton={isDismissable}>
				<Modal.Title>Select {providerName} Resources</Modal.Title>
			</Modal.Header>
			<Modal.Body style={{ height: "65vh", padding: "0" }}>
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
						paginationPageSize={15}
					/>
				</div>
			</Modal.Body>
			<Modal.Footer>
				<div className="d-flex justify-content-between align-items-center w-100">
					<div
						className="selected-count"
						style={{
							fontSize: "1rem",
							fontWeight: "600",
							color: selectedResources.length > 0 ? "#198754" : "#6c757d",
						}}>
						{selectedResources.length} resource{selectedResources.length !== 1 ? "s" : ""} selected
					</div>
					<div className="d-flex gap-2">
						{isDismissable && (
							<Button variant="secondary" onClick={handleClose}>
								Cancel
							</Button>
						)}
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
