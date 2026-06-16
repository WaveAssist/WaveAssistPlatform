import React, { useState, useCallback, useEffect, useMemo, useRef } from "react";
import Modal from "react-bootstrap/Modal";
import { Button, Form } from "react-bootstrap";
import { useToast } from "../utils/toast_context";
import { computeAutoSelection } from "./resourceAutoSelect";
import "./ResourceSelectionPopup.css";

interface Resource {
	id: string;
	name: string;
	extra?: any;
	properties?: Record<string, any>;
	sort_key?: string | null;
	archived?: boolean;
}

interface PropertyOption {
	name: string;
	key: string;
}

interface ResourcePropertyConfig {
	key: string;
	display_name: string;
	type: "select" | "text";
	is_optional?: boolean; // default true when omitted (optional)
	default_value?: string;
	helper_message?: string;
	options?: PropertyOption[];
}

interface ResourceSelectionPopupProps {
	isOpen: boolean;
	onClose: () => void;
	resources: Resource[];
	onSave: (selectedResources: Resource[]) => void;
	providerName: string;
	isDismissable?: boolean;
	initiallySelectedResources?: Resource[];
	resourceProperties?: ResourcePropertyConfig[];
}

const PAGE_SIZE_OPTIONS = [10, 15, 25, 50];
const DEFAULT_PAGE_SIZE = 15;

const ResourceSelectionPopup: React.FC<ResourceSelectionPopupProps> = ({
	isOpen,
	onClose,
	resources,
	onSave,
	providerName,
	isDismissable = true,
	initiallySelectedResources = [],
	resourceProperties = [],
}) => {
	const { showToast } = useToast();
	const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
	const [expandedRowId, setExpandedRowId] = useState<string | null>(null); // only one open at a time
	const [resourcePropertiesState, setResourcePropertiesState] = useState<Record<string, Record<string, any>>>({});
	const [filterText, setFilterText] = useState("");
	const [page, setPage] = useState(1);
	const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
	const [autoSelectNotice, setAutoSelectNotice] = useState<string>("");
	// Initialize selection exactly ONCE per open. Without this, the effect's other deps
	// (initiallySelectedResources / resources) change identity on any parent re-render (e.g. a toast
	// auto-dismiss) and re-run the effect, clobbering the user's in-progress selection edits.
	const initializedRef = useRef(false);

	const hasProperties = resourceProperties.length > 0;

	const buildDefaultProperties = useCallback((): Record<string, any> => {
		const defaults: Record<string, any> = {};
		for (const prop of resourceProperties) {
			defaults[prop.key] = prop.default_value ?? "";
		}
		return defaults;
	}, [resourceProperties]);

	// Initialize selection and props when modal opens (all rows collapsed; only Select opens them).
	// First connect (no saved selection) auto-preselects via computeAutoSelection so it is
	// connect-and-done; a saved selection is respected and never clobbered.
	useEffect(() => {
		if (!isOpen) {
			initializedRef.current = false; // reset so the NEXT open initializes once
			return;
		}
		if (initializedRef.current) return; // already initialized for this open — never clobber edits
		initializedRef.current = true;

		const hasSavedSelection = initiallySelectedResources.length > 0;
		let ids: Set<string>;
		if (hasSavedSelection) {
			ids = new Set(initiallySelectedResources.map((r) => r.id));
			setAutoSelectNotice("");
		} else {
			const auto = computeAutoSelection(resources, hasSavedSelection);
			ids = new Set(auto.ids);
			setAutoSelectNotice(auto.notice);
		}
		setSelectedIds(ids);
		setExpandedRowId(null); // Default all collapsed; expand only when user clicks Select
		const propsMap: Record<string, Record<string, any>> = {};
		for (const res of initiallySelectedResources) {
			propsMap[res.id] = res.properties ? { ...res.properties } : buildDefaultProperties();
		}
		setResourcePropertiesState(propsMap);
		setFilterText("");
		setPage(1);
	}, [isOpen, initiallySelectedResources, resources, buildDefaultProperties]);

	const filteredResources = useMemo(() => {
		if (!filterText.trim()) return resources;
		const q = filterText.trim().toLowerCase();
		return resources.filter((r) => r.id.toLowerCase().includes(q) || (r.name && r.name.toLowerCase().includes(q)));
	}, [resources, filterText]);

	const totalPages = Math.max(1, Math.ceil(filteredResources.length / pageSize));
	const paginatedResources = useMemo(() => {
		const start = (page - 1) * pageSize;
		return filteredResources.slice(start, start + pageSize);
	}, [filteredResources, page, pageSize]);

	const selectedResources = useMemo(
		() => resources.filter((r) => selectedIds.has(r.id)),
		[resources, selectedIds]
	);

	const toggleSelect = useCallback(
		(resourceId: string) => {
			setSelectedIds((prev) => {
				const next = new Set(prev);
				if (next.has(resourceId)) {
					next.delete(resourceId);
					setExpandedRowId((current) => (current === resourceId ? null : current));
				} else {
					next.add(resourceId);
					setExpandedRowId(resourceId); // open this one, close any other
					setResourcePropertiesState((p) => ({
						...p,
						[resourceId]: p[resourceId] || buildDefaultProperties(),
					}));
				}
				return next;
			});
		},
		[buildDefaultProperties]
	);

	const toggleExpand = useCallback((resourceId: string) => {
		setExpandedRowId((current) => (current === resourceId ? null : resourceId)); // open this one only, or close if already open
	}, []);

	// Bulk: add every currently-filtered resource to the selection (search-aware).
	const selectAllFiltered = useCallback(() => {
		setSelectedIds((prev) => {
			const next = new Set(prev);
			for (const r of filteredResources) {
				next.add(r.id);
			}
			return next;
		});
		setResourcePropertiesState((prev) => {
			const next = { ...prev };
			for (const r of filteredResources) {
				if (!next[r.id]) next[r.id] = buildDefaultProperties();
			}
			return next;
		});
		setAutoSelectNotice("");
	}, [filteredResources, buildDefaultProperties]);

	// Bulk: clear the entire selection.
	const clearAll = useCallback(() => {
		setSelectedIds(new Set());
		setExpandedRowId(null);
		setAutoSelectNotice("");
	}, []);

	const handlePropertyChange = (resourceId: string, propKey: string, value: string) => {
		setResourcePropertiesState((prev) => ({
			...prev,
			[resourceId]: {
				...(prev[resourceId] || buildDefaultProperties()),
				[propKey]: value,
			},
		}));
	};

	const handleSave = () => {
		if (hasProperties) {
			const requiredProps = resourceProperties.filter((p) => p.is_optional === false);
			for (const res of selectedResources) {
				const props = resourcePropertiesState[res.id] || buildDefaultProperties();
				for (const prop of requiredProps) {
					const val = props[prop.key];
					if (val == null || String(val).trim() === "") {
						showToast(`"${prop.display_name}" is required for ${res.id}.`, "warning");
						return;
					}
				}
			}
		}
		let enrichedResources = selectedResources;
		if (hasProperties) {
			enrichedResources = selectedResources.map((res) => ({
				...res,
				properties: resourcePropertiesState[res.id] || buildDefaultProperties(),
			}));
		}
		onSave(enrichedResources);
		onClose();
	};

	const handleClose = () => {
		setSelectedIds(new Set());
		setExpandedRowId(null);
		setResourcePropertiesState({});
		setAutoSelectNotice("");
		onClose();
	};

	return (
		<Modal show={isOpen} onHide={handleClose} size="xl" centered backdrop="static" className="resource-selection-popup">
			<Modal.Header closeButton={isDismissable}>
				<Modal.Title>Select {providerName} Resources</Modal.Title>
			</Modal.Header>
			<Modal.Body className="resource-selection-popup-body">
				{/* Search: full width above table */}
				<div className="resource-search-wrapper">
					<Form.Control
						type="text"
						placeholder="Search..."
						value={filterText}
						onChange={(e) => {
							setFilterText(e.target.value);
							setPage(1);
						}}
						className="resource-search-input"
						aria-label="Search resources"
					/>
				</div>

				{autoSelectNotice && <div className="resource-autoselect-notice">{autoSelectNotice}</div>}

				<div className="resource-bulk-actions">
					<Button
						variant="outline-secondary"
						size="sm"
						onClick={selectAllFiltered}
						disabled={filteredResources.length === 0}
						aria-label="Select all filtered resources"
						className="resource-bulk-btn">
						Select all{filterText.trim() ? " (filtered)" : ""}
					</Button>
					<Button
						variant="outline-secondary"
						size="sm"
						onClick={clearAll}
						disabled={selectedIds.size === 0}
						aria-label="Clear all selected resources"
						className="resource-bulk-btn">
						Clear all
					</Button>
				</div>

				<div className="resource-table-wrapper">
					<table className="resource-table">
						<thead>
							<tr>
								{hasProperties && <th className="resource-table-col-chevron" style={{ width: 30 }} aria-label="Expand" />}
								<th className="resource-table-col-name">Name</th>
								<th className="resource-table-col-select" style={{ width: 150 }}>
									Select
								</th>
							</tr>
						</thead>
						<tbody>
							{paginatedResources.map((resource) => {
								const isSelected = selectedIds.has(resource.id);
								const isExpanded = expandedRowId === resource.id;
								return (
									<React.Fragment key={resource.id}>
										<tr
											className={`resource-table-row ${isSelected ? "resource-table-row-selected" : ""} ${isExpanded ? "resource-table-row-expanded" : ""}`}
											onClick={() => toggleSelect(resource.id)}
											role="button"
											tabIndex={0}
											onKeyDown={(e) => {
												if (e.key === "Enter" || e.key === " ") {
													e.preventDefault();
													toggleSelect(resource.id);
												}
											}}
											aria-expanded={isSelected ? isExpanded : undefined}>
											{hasProperties && (
												<td className="resource-table-col-chevron align-middle">
													{isSelected ? (
														<span
															className={`resource-table-chevron ${isExpanded ? "resource-table-chevron-expanded" : ""}`}
															onClick={(e) => {
																e.stopPropagation();
																toggleExpand(resource.id);
															}}
															aria-hidden>
															<i className="bi bi-chevron-right" />
														</span>
													) : (
														<span className="resource-table-chevron-placeholder" aria-hidden />
													)}
												</td>
											)}
											<td className="align-middle resource-table-cell-name">{resource.name}</td>
											<td className="align-middle resource-table-cell-select">
												<Button
													variant={isSelected ? "primary" : "outline-secondary"}
													size="sm"
													onClick={(e) => {
														e.stopPropagation();
														toggleSelect(resource.id);
													}}
													className="resource-table-select-btn">
													{isSelected ? "Selected" : "Select"}
												</Button>
											</td>
										</tr>
										{hasProperties && isSelected && isExpanded && (
											<tr className="resource-table-detail-row">
												<td colSpan={hasProperties ? 3 : 2} className="resource-table-detail-cell">
													<div className="resource-table-detail-content">
														{resourceProperties.map((prop) => (
															<div
																key={prop.key}
																className={prop.type === "text" ? "resource-table-detail-field flex-grow-1" : "resource-table-detail-field resource-table-detail-field-fixed"}>
																<Form.Label className="resource-table-detail-label">
																	{prop.display_name}
																	{prop.is_optional !== false && (
																		<span className="resource-table-detail-optional"> (optional)</span>
																	)}
																</Form.Label>
																{prop.type === "select" && prop.options ? (
																	<Form.Select
																		size="sm"
																		value={(resourcePropertiesState[resource.id] || {})[prop.key] ?? prop.default_value ?? ""}
																		onChange={(e) => handlePropertyChange(resource.id, prop.key, e.target.value)}
																		className="resource-table-detail-input"
																		onClick={(e) => e.stopPropagation()}>
																		{prop.options.map((opt) => (
																			<option key={opt.key} value={opt.key}>
																				{opt.name}
																			</option>
																		))}
																	</Form.Select>
																) : (
																	<Form.Control
																		size="sm"
																		type="text"
																		placeholder={prop.helper_message || "Optional"}
																		value={(resourcePropertiesState[resource.id] || {})[prop.key] ?? prop.default_value ?? ""}
																		onChange={(e) => handlePropertyChange(resource.id, prop.key, e.target.value)}
																		className="resource-table-detail-input"
																		onClick={(e) => e.stopPropagation()}
																	/>
																)}
															</div>
														))}
													</div>
												</td>
											</tr>
										)}
									</React.Fragment>
								);
							})}
						</tbody>
					</table>
				</div>

				{/* Pagination */}
				<div className="resource-table-pagination">
					<div className="d-flex align-items-center gap-2">
						<Form.Select
							size="sm"
							value={pageSize}
							onChange={(e) => {
								setPageSize(Number(e.target.value));
								setPage(1);
							}}
							className="resource-table-pagesize"
							aria-label="Page size">
							{PAGE_SIZE_OPTIONS.map((n) => (
								<option key={n} value={n}>
									{n} per page
								</option>
							))}
						</Form.Select>
						<span className="resource-table-pagination-info">
							Page {page} of {totalPages} ({filteredResources.length} total)
						</span>
					</div>
					<div className="d-flex gap-1">
						<Button
							variant="outline-secondary"
							size="sm"
							onClick={() => setPage((p) => Math.max(1, p - 1))}
							disabled={page <= 1}
							aria-label="Previous page">
							<i className="bi bi-chevron-left" />
						</Button>
						<Button
							variant="outline-secondary"
							size="sm"
							onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
							disabled={page >= totalPages}
							aria-label="Next page">
							<i className="bi bi-chevron-right" />
						</Button>
					</div>
				</div>
			</Modal.Body>
			<Modal.Footer>
				<div className="d-flex justify-content-between align-items-center w-100">
					<div
						className="resource-selection-count"
						style={{
							fontSize: "1rem",
							fontWeight: "600",
							color: selectedResources.length > 0 ? "var(--color-primary)" : "var(--color-text-secondary)",
						}}>
						{selectedResources.length} resource{selectedResources.length !== 1 ? "s" : ""} selected
					</div>
					<div className="d-flex gap-2">
						{isDismissable && (
							<Button variant="secondary" onClick={handleClose}>
								Cancel
							</Button>
						)}
						<Button variant="primary" onClick={handleSave} disabled={selectedResources.length === 0} className="btn-primary-wa">
							Save Selection
						</Button>
					</div>
				</div>
			</Modal.Footer>
		</Modal>
	);
};

export default ResourceSelectionPopup;
