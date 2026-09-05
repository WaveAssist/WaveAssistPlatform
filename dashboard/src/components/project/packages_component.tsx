import React, { useEffect, useState } from "react";
import { fetchPackagesApi, removePackageApi, reinstallPackageApi, installPackageApi } from "../../services/project_services";
import { useToast } from "../../utils/toast_context";
import { Button } from "react-bootstrap";
import { AgGridReact } from "ag-grid-react";
import "./project_components.css";
import "../../utils/ag-theme-project.css";
import Modal from "react-bootstrap/Modal";
import { useRefresh } from "../../utils/RefreshContext";
import "ag-grid-community/styles/ag-theme-balham.css";
import PaywallBlock from "../PaywallBlock";

const PackagesComponent: React.FC = () => {
	const [packagesArray, setPackagesArray] = useState<any[]>([]);
	const { showToast } = useToast();
	const [showPackageEditor, setShowPackageEditor] = useState(false);
	const [loading, setLoading] = useState(false);
	const { shouldRefresh } = useRefresh();
	const [packageName, setPackageName] = useState("");
	const [packageVersion, setPackageVersion] = useState("");

	const shouldBlockPackages = true;

	const handleCloseVariableEditor = () => {
		setShowPackageEditor(false);
	};

	const fetchPackages = async () => {
		if (shouldBlockPackages) {
			setPackagesArray([]);
			setLoading(false);
			return;
		}
		try {
			setLoading(true);
			const response = await fetchPackagesApi();
			if (response && response.packages_array) {
				setPackagesArray(response.packages_array);
			} else {
				showToast("Failed to fetch packages", "danger");
			}
			setLoading(false);
		} catch (error) {
			console.error("FetchPackages failed:", error);
			showToast("Something went wrong with loading packages, please try again.", "danger");
			setLoading(false);
		}
	};

	const handleShowVariableEditor = () => {
		if (shouldBlockPackages) return;
		setPackageName("");
		setPackageVersion("");
		setShowPackageEditor(true);
	};

	const gridOptions = {
		suppressCellFocus: true,
	};

	useEffect(() => {
		fetchPackages();
	}, [shouldRefresh]);

	const defaultColDef = {
		autoHeight: true,
		wrapText: true,
		enableCellChangeFlash: true,
		editable: false,
		cellClass: "ag-cell",
		sortable: true,
		filter: true,
		resizable: true,
		cellStyle: { display: "flex", alignItems: "center" }, // Center content vertically
	};

	const handleDelete = async (packageDict: any) => {
		if (shouldBlockPackages) return;
		var package_name = packageDict.package_name;
		var message = "Are you sure you want to remove this package: " + package_name + "?";
		const confirmDelete = window.confirm(message);
		if (!confirmDelete) {
			return;
		}
		try {
			await removePackageApi(package_name);
			showToast("Package deleted successfully.", "success");
			fetchPackages();
		} catch (error) {
			console.error("DeletePackage failed:", error);
			showToast("Could not remove package: " + error, "danger");
		}
	};

	const handleReinstall = async (packageDict: any) => {
		if (shouldBlockPackages) return;
		var package_name = packageDict.package_name;
		var message = "Are you sure you want to reinstall & upgrade this package: " + package_name + "?";
		const confirmReinstall = window.confirm(message);
		if (!confirmReinstall) {
			return;
		}
		try {
			await reinstallPackageApi(package_name);
			showToast("Package reinstalled successfully.", "success");
			fetchPackages();
		} catch (error) {
			console.error("ReinstallPackage failed:", error);
			showToast("Could not reinstall package: " + error, "danger");
		}
	};

	const handleAddPackage = async () => {
		if (shouldBlockPackages) return;
		try {
			if (!packageName) {
				showToast("Package Name is required.", "danger");
				return;
			}
			handleCloseVariableEditor();
			setLoading(true);
			await installPackageApi(packageName, packageVersion);
			showToast("Package added successfully.", "success");
			fetchPackages();
			handleCloseVariableEditor();
		} catch (error) {
			console.error("AddPackage failed:", error);
			showToast("Could not add package: " + error, "danger");
		} finally {
			setLoading(false);
		}
	};

	const ActionButtons = (params: any) => {
		return (
			<div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
				<Button
					variant="dark"
					size="sm"
					style={{ padding: "2px 6px", fontSize: "12px", lineHeight: "1" }}
					onClick={() => handleReinstall(params.data)}>
					<i className="bi bi-arrow-clockwise"></i>
				</Button>
				<Button
					variant="danger"
					size="sm"
					style={{ padding: "2px 6px", fontSize: "12px", lineHeight: "1" }}
					onClick={() => handleDelete(params.data)}>
					<i className="bi bi-trash"></i>
				</Button>
			</div>
		);
	};

	const columnDefs = [
		{ headerName: "Package Name", field: "package_name", flex: 3, minWidth: 150, resizable: true }, // Expands to fill space
		{
			headerName: "Package Version",
			field: "package_version",
			flex: 2,
			minWidth: 120,
			resizable: true,
			cellRenderer: (params: any) => <span className="badge badge-primary">{params.value}</span>,
			cellStyle: { display: "flex", alignItems: "center" }, // Centering content vertically
		},
		{ headerName: "Actions", cellRenderer: ActionButtons, width: 160, minWidth: 120, resizable: true },
	];

	return (
		<div className="main-container">
			<div className="mt-3 d-flex flex-column" style={{ height: "100%" }}>
				<div style={{ flex: "0 0 100%", display: "flex", flexDirection: "column" }}>
					<div className="d-flex justify-content-between align-items-center mb-3 ">
						<h3 className="translucent_white">Packages</h3>
						<div>
							<Button variant="dark" onClick={handleShowVariableEditor}>
								<span className="bi bi-plus-lg"></span>
							</Button>{" "}
						</div>
					</div>

					{loading && packagesArray.length === 0 ? (
						<div className="d-flex justify-content-center align-items-center" style={{ flex: 1, minHeight: "400px" }}>
							<div className="text-center">
								<div className="spinner-border text-success mb-3" role="status" style={{ width: "3rem", height: "3rem" }}>
									<span className="visually-hidden">Loading...</span>
								</div>
								<div className="text-white">Loading packages...</div>
							</div>
						</div>
					) : (
						<div className="ag-theme-balham-dark grid-container full-screen">
							<AgGridReact
								rowData={packagesArray}
								columnDefs={columnDefs}
								pagination={true}
								paginationPageSize={10}
								gridOptions={gridOptions}
								defaultColDef={defaultColDef}
							/>
						</div>
					)}
				</div>
			</div>

			<Modal show={showPackageEditor} onHide={handleCloseVariableEditor} size="lg" centered>
				<Modal.Header closeButton>
					<Modal.Title>Add Package</Modal.Title>
				</Modal.Header>
				<Modal.Body>
					<label htmlFor="variableKey" className="form-label">
						Package Name
					</label>
					<input type="text" className="form-control" id="packageName" value={packageName} onChange={(e) => setPackageName(e.target.value)} />
					<br></br>
					<label htmlFor="variableKey" className="form-label">
						Package Version (Optional)
					</label>
					<input
						type="text"
						className="form-control"
						id="packageVersion"
						value={packageVersion}
						onChange={(e) => setPackageVersion(e.target.value)}
					/>
					<br></br>

					<Modal.Footer>
						<Button variant="secondary" onClick={handleCloseVariableEditor}>
							Close
						</Button>
						<Button variant="primary" onClick={handleAddPackage}>
							Add
						</Button>
					</Modal.Footer>
				</Modal.Body>
			</Modal>
			<PaywallBlock show={shouldBlockPackages} showUpgradeButton={false} message="Package management is currently disabled." />
		</div>
	);
};

export default PackagesComponent;
