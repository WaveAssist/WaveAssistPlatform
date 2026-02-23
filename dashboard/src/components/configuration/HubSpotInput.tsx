import React, { useEffect, useState } from "react";
import { Button, Modal, Form, Spinner } from "react-bootstrap";
import { callApi } from "../../services/base_service";
import { setDataForKeyApi } from "../../services/project_services";
import { useToast } from "../../utils/toast_context";
import hubspotLogo from "../../assets/uploads/hubspot-logo.png";

interface HubSpotInputProps {
	value: string;
	onChange?: (value: string) => void;
	selectResources?: (inputData: any) => void;
	selectedResources?: any;
	inputData?: any;
	onRefresh?: () => void;
}

const HubSpotInput: React.FC<HubSpotInputProps> = ({
	value,
	onChange,
	selectResources,
	selectedResources,
	inputData,
	onRefresh,
}) => {
	const [isLoading, setIsLoading] = useState(false);
	const [isSelectingResources, setIsSelectingResources] = useState(false);
	const [showManualModal, setShowManualModal] = useState(false);
	const [manualToken, setManualToken] = useState("");
	const [isSubmittingToken, setIsSubmittingToken] = useState(false);
	const [showPopupMessage, setShowPopupMessage] = useState(false);
	const [authUrl, setAuthUrl] = useState("");
	const [popupBlocked, setPopupBlocked] = useState(false);
	const { showToast } = useToast();

	// Pre-fill manual token with current value when modal opens
	useEffect(() => {
		if (showManualModal && value && value !== "" && value !== "null" && value !== "undefined") {
			setManualToken(value);
		}
	}, [showManualModal, value]);

	const handleSelectResources = async () => {
		if (selectResources && inputData) {
			try {
				setIsSelectingResources(true);
				await selectResources(inputData);
			} catch (error) {
				console.error("Error selecting HubSpot resources:", error);
			} finally {
				setIsSelectingResources(false);
			}
		}
	};

	const handleConnectHubSpot = async () => {
		try {
			setIsLoading(true);
			setPopupBlocked(false);
			setShowPopupMessage(false);

			const uid = localStorage.getItem("uid");
			const projectKey = localStorage.getItem("selected_project_key");

			if (!uid || !projectKey) {
				throw new Error("Missing user ID or project key");
			}

			const body = new URLSearchParams({
				uid: uid,
				project_key: projectKey,
				provider_name: "hubspot",
			});

			const response = await callApi("providers/initiate/", body);

			if (response && response.auth_url) {
				setAuthUrl(response.auth_url);

				const popup = window.open(response.auth_url, "_blank");

				if (!popup || popup.closed || typeof popup.closed === "undefined") {
					setPopupBlocked(true);
					setShowPopupMessage(true);
				} else {
					setShowPopupMessage(true);
					setTimeout(() => {
						if (popup.closed) {
							setPopupBlocked(true);
						}
					}, 1000);
				}
			} else {
				throw new Error("No auth URL received from server");
			}
		} catch (error) {
			console.error("Error initiating HubSpot connection:", error);
			alert("Failed to initiate HubSpot connection. Please try again.");
		} finally {
			setIsLoading(false);
		}
	};

	const handleRetryPopup = () => {
		if (authUrl) {
			const popup = window.open(authUrl, "_blank");
			if (!popup || popup.closed || typeof popup.closed === "undefined") {
				setPopupBlocked(true);
			} else {
				setPopupBlocked(false);
				setShowPopupMessage(true);
			}
		}
	};

	const handleManualTokenSubmit = async () => {
		try {
			setIsSubmittingToken(true);

			await setDataForKeyApi(manualToken, "hubspot_access_token", "string");
			showToast("HubSpot token saved successfully!", "success");

			if (onChange) {
				onChange(manualToken);
			}

			setShowManualModal(false);
			setManualToken("");

			if (onRefresh) {
				await onRefresh();
			}

			if (selectResources && inputData) {
				try {
					handleSelectResources();
				} catch (error) {
					console.error("Error auto-selecting HubSpot resources after token save:", error);
				}
			}
		} catch (error) {
			console.error("Error saving HubSpot token:", error);
			showToast("Failed to save HubSpot token. Please try again.", "danger");
		} finally {
			setIsSubmittingToken(false);
		}
	};

	const isConfigured = value && value !== "" && value !== "null" && value !== "undefined";
	const selectedResourcesCount = Array.isArray(selectedResources) ? selectedResources.length : 0;

	const manualTokenModal = (
		<Modal
			show={showManualModal}
			onHide={() => {
				setShowManualModal(false);
				setManualToken("");
			}}
			centered>
			<Modal.Header closeButton>
				<Modal.Title>Enter HubSpot Access Token</Modal.Title>
			</Modal.Header>
			<Modal.Body>
				<Form.Group>
					<Form.Label className="text-white mb-2">HubSpot Private App Token</Form.Label>
					<Form.Control
						type="text"
						placeholder="pat-xxxx..."
						value={manualToken}
						autoComplete="off"
						onChange={(e) => setManualToken(e.target.value)}
						autoFocus
					/>
					<p className="text-white mt-2 small">
						Use a HubSpot Private App token with permission to read lists/contacts. You can always rotate or revoke this token from HubSpot.
					</p>
				</Form.Group>
			</Modal.Body>
			<Modal.Footer>
				<Button
					variant="secondary"
					onClick={() => {
						setShowManualModal(false);
						setManualToken("");
					}}
					disabled={isSubmittingToken}>
					Cancel
				</Button>
				<Button variant="primary" onClick={handleManualTokenSubmit} disabled={!manualToken.trim() || isSubmittingToken}>
					{isSubmittingToken ? (
						<>
							<span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
							Saving...
						</>
					) : (
						"Submit"
					)}
				</Button>
			</Modal.Footer>
		</Modal>
	);

	const popupMessage = showPopupMessage && (
		<div className="mt-3 p-3 border rounded" style={{ backgroundColor: "#1C1F28", borderColor: "#1ED66C" }}>
			<div className="d-flex align-items-center gap-2">
				<svg width="20" height="20" viewBox="0 0 24 24" fill="#1ED66C">
					<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
				</svg>
				<div className="flex-grow-1">
					<div className="fw-medium text-white mb-1">HubSpot Authorization</div>
					{popupBlocked ? (
						<div className="small" style={{ color: "#A1A1AA" }}>
							Popup was blocked by your browser.
							<button className="btn btn-link p-0 text-white text-decoration-none ms-1" onClick={handleRetryPopup} style={{ fontSize: "inherit" }}>
								Click here to open again
							</button>
						</div>
					) : (
						<div className="small" style={{ color: "#A1A1AA" }}>
							Please continue the HubSpot authorization flow in the new window that opened.
						</div>
					)}
				</div>
				<button className="btn-close btn-close-sm btn-close-white" onClick={() => setShowPopupMessage(false)} aria-label="Close"></button>
			</div>
		</div>
	);

	if (isConfigured) {
		return (
			<>
				<div className="hubspot-input-container">
					<div
						className="p-3 border rounded"
						style={{
							backgroundColor: "#1C1F28",
							borderColor: "#2D313A",
						}}>
						<div className="d-flex align-items-center justify-content-between flex-wrap gap-3">
							<div className="d-flex align-items-center gap-3">
								<div
									style={{
										width: 32,
										height: 32,
										borderRadius: "50%",
										overflow: "hidden",
										background: "#FF7A59",
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
									}}>
									<img
										src={hubspotLogo}
										alt="HubSpot logo"
										style={{
											width: "95%",
											height: "95%",
											objectFit: "cover",
										}}
									/>
								</div>
								<div>
									<div className="fw-medium text-white" style={{ fontSize: "0.95rem" }}>
										HubSpot Integration
									</div>
									<div className="text-success small d-flex align-items-center gap-1">
										<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
											<path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
										</svg>
										Connected to HubSpot
									</div>
									{selectedResourcesCount > 0 && (
										<div className="small" style={{ color: "#A1A1AA" }}>
											{selectedResourcesCount} list{selectedResourcesCount !== 1 ? "s" : ""} selected
										</div>
									)}
								</div>
							</div>
							<div className="d-flex flex-column align-items-end gap-1">
								<Button
									variant="outline-success"
									size="sm"
									onClick={handleConnectHubSpot}
									style={{
										display: "flex",
										alignItems: "center",
										gap: "6px",
										fontWeight: 500,
										padding: "6px 12px",
										borderRadius: "6px",
										fontSize: "0.875rem",
										transition: "all 0.2s ease",
									}}>
									Reconnect
								</Button>
							</div>
						</div>
					</div>
				</div>
				{popupMessage}
				{manualTokenModal}
				{isSelectingResources && (
					<div
						style={{
							position: "fixed",
							top: 0,
							left: 0,
							right: 0,
							bottom: 0,
							backgroundColor: "rgba(0, 0, 0, 0.5)",
							display: "flex",
							flexDirection: "column",
							justifyContent: "center",
							alignItems: "center",
							zIndex: 9999,
						}}>
						<Spinner animation="border" role="status" variant="light" style={{ width: "3rem", height: "3rem" }}>
							<span className="visually-hidden">Loading...</span>
						</Spinner>
						<p className="text-white mt-3" style={{ fontSize: "1.1rem", fontWeight: 500 }}>
							Fetching lists...
						</p>
					</div>
				)}
			</>
		);
	}

	return (
		<>
			<div className="hubspot-input-container">
				<div
					className="p-3 border rounded"
					style={{
						backgroundColor: "#1C1F28",
						borderColor: "#2D313A",
					}}>
					<div className="d-flex align-items-center justify-content-between flex-wrap gap-3">
						<div className="d-flex align-items-center gap-3">
							<div
								style={{
									width: 32,
									height: 32,
									borderRadius: "50%",
									overflow: "hidden",
									background: "#FF7A59",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
								}}>
								<img
									src={hubspotLogo}
									alt="HubSpot logo"
									style={{
										width: "95%",
										height: "95%",
										objectFit: "cover",
									}}
								/>
							</div>
							<div>
								<div className="fw-medium text-white" style={{ fontSize: "0.95rem" }}>
									HubSpot Integration
								</div>
								<div className="text-secondary small">Connect HubSpot to share specific lists with this assistant.</div>
							</div>
						</div>
						<div className="d-flex flex-column align-items-end gap-1">
							<Button
								variant="primary"
								size="sm"
								onClick={handleConnectHubSpot}
								disabled={isLoading}
								style={{
									display: "flex",
									alignItems: "center",
									gap: "6px",
									fontWeight: 600,
									padding: "6px 24px",
									borderRadius: "6px",
									fontSize: "0.875rem",
									transition: "all 0.2s ease",
								}}>
								{isLoading ? "Connecting..." : "Connect HubSpot"}
							</Button>
							<a
								href="#"
								onClick={(e) => {
									e.preventDefault();
									setShowManualModal(true);
								}}
								style={{
									fontSize: "0.75rem",
									color: "#A1A1AA",
									textDecoration: "none",
								}}
								onMouseEnter={(e) => (e.currentTarget.style.textDecoration = "underline")}
								onMouseLeave={(e) => (e.currentTarget.style.textDecoration = "none")}>
								or manually enter your token
							</a>
						</div>
					</div>
				</div>
			</div>
			{popupMessage}
			{manualTokenModal}
		</>
	);
};

export default HubSpotInput;

