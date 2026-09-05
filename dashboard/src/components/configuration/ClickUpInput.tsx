import React, { useState, useEffect } from "react";
import { Button } from "react-bootstrap";
import { callApi } from "../../services/base_service";
import { useToast } from "../../utils/toast_context";
import clickupLogo from "../../assets/uploads/clickup-logo.png";

interface ClickUpInputProps {
	value: string;
	selectResources?: (inputData: any) => void;
	inputData?: any;
	highlightSelectResources?: boolean;
	onRefresh?: () => void;
}

const ClickUpInput: React.FC<ClickUpInputProps> = ({
	value,
	selectResources,
	inputData,
	highlightSelectResources = false,
	onRefresh,
}) => {
	const [isLoading, setIsLoading] = useState(false);
	const [isSelectingResources, setIsSelectingResources] = useState(false);
	const [authUrl, setAuthUrl] = useState("");
	const [showPopupMessage, setShowPopupMessage] = useState(false);
	const [popupBlocked, setPopupBlocked] = useState(false);
	const { showToast } = useToast();

	const handleSelectResources = async () => {
		if (selectResources && inputData) {
			try {
				setIsSelectingResources(true);
				await selectResources(inputData);

				// Refresh wizard data so the UI reflects any newly selected resources
				if (onRefresh) {
					await onRefresh();
				}
			} catch (error) {
				console.error("Error selecting resources:", error);
			} finally {
				setIsSelectingResources(false);
			}
		}
	};

	useEffect(() => {
		if (value === "connected" && selectResources && inputData) {
			handleSelectResources();
		}
	}, [value, selectResources, inputData]);

	const handleConnectClickUp = async () => {
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
				provider_name: "clickup",
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
			console.error("Error initiating ClickUp connection:", error);
			showToast("Failed to initiate ClickUp connection. Please try again.", "danger");
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

	const getButtonText = () => {
		if (isLoading) return "Connecting...";
		if (value === "connecting") return "Connecting to ClickUp...";
		if (value === "connected") return "Connected to ClickUp";
		return "Connect ClickUp";
	};

	const isDisabled = isLoading || value === "connecting" || value === "connected";
	const isConfigured = value && value !== "" && value !== "null" && value !== "undefined";

	const cardStyle = { backgroundColor: "var(--color-bg-card)", border: "1px solid var(--color-border)" };
	const textMutedStyle = { color: "var(--color-text-secondary)" };

	if (isConfigured && value !== "connecting") {
		return (
			<div className="clickup-input-container">
				<div className="p-3 border rounded" style={cardStyle}>
					<div className="d-flex align-items-center justify-content-between d-none d-sm-flex">
						<div className="d-flex align-items-center gap-3">
							<div
								style={{
									width: 32,
									height: 32,
									borderRadius: "50%",
									overflow: "hidden",
									background: "#7B68EE",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
								}}>
								<img
									src={clickupLogo}
									alt="ClickUp logo"
									style={{
										width: "90%",
										height: "90%",
										objectFit: "contain",
									}}
								/>
							</div>
							<div>
								<div className="fw-medium text-white" style={{ fontSize: "0.95rem" }}>ClickUp Integration</div>
								<div className="text-success small d-flex align-items-center gap-1">
									<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
										<path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
									</svg>
									Connected to ClickUp
								</div>
							</div>
						</div>
						<div className="d-flex gap-2">
							<Button
								variant="primary"
								size="sm"
								onClick={handleSelectResources}
								disabled={isSelectingResources}
								className={`clickup-action-button ${highlightSelectResources ? "highlight-pulse" : ""}`}
								style={{
									display: "flex",
									alignItems: "center",
									gap: "6px",
									fontWeight: "500",
									padding: "6px 12px",
									borderRadius: "6px",
									fontSize: "0.875rem",
									transition: "all 0.2s ease",
								}}>
								{isSelectingResources ? (
									<>
										<span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
										Loading...
									</>
								) : (
									"Select Projects"
								)}
							</Button>

							<Button
								variant="outline-success"
								size="sm"
								onClick={handleConnectClickUp}
								className="clickup-action-button"
								style={{
									display: "flex",
									alignItems: "center",
									gap: "6px",
									fontWeight: "500",
									padding: "6px 12px",
									borderRadius: "6px",
									fontSize: "0.875rem",
									transition: "all 0.2s ease",
								}}>
								Reconnect
							</Button>
						</div>
					</div>

					{/* Mobile */}
					<div className="d-flex d-sm-none flex-column">
						<div className="d-flex align-items-center gap-3 mb-3">
							<div
								style={{
									width: 32,
									height: 32,
									borderRadius: "50%",
									overflow: "hidden",
									background: "#7B68EE",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
								}}>
								<img
									src={clickupLogo}
									alt="ClickUp logo"
									style={{
										width: "90%",
										height: "90%",
										objectFit: "contain",
									}}
								/>
							</div>
							<div>
								<div className="fw-medium text-white" style={{ fontSize: "0.95rem" }}>ClickUp Integration</div>
								<div className="text-success small d-flex align-items-center gap-1">
									<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
										<path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
									</svg>
									Connected to ClickUp
								</div>
							</div>
						</div>
						<div className="d-flex flex-column gap-2">
							<Button
								variant="primary"
								size="sm"
								onClick={handleSelectResources}
								disabled={isSelectingResources}
								className={`clickup-action-button ${highlightSelectResources ? "highlight-pulse" : ""}`}
								style={{
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									gap: "6px",
									fontWeight: "500",
									padding: "8px 16px",
									borderRadius: "6px",
									fontSize: "0.875rem",
									transition: "all 0.2s ease",
								}}>
								{isSelectingResources ? (
									<>
										<span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
										Loading...
									</>
								) : (
									"Select Projects"
								)}
							</Button>

							<Button
								variant="outline-success"
								size="sm"
								onClick={handleConnectClickUp}
								className="clickup-action-button"
								style={{
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									gap: "6px",
									fontWeight: "500",
									padding: "8px 16px",
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
		);
	}

	const popupMessage = showPopupMessage && (
		<div className="mt-3 p-3 border rounded" style={{ backgroundColor: "var(--color-bg-card)", borderColor: "var(--color-primary)" }}>
			<div className="d-flex align-items-center gap-2">
				<svg width="20" height="20" viewBox="0 0 24 24" style={{ fill: "var(--color-primary)" }}>
					<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
				</svg>
				<div className="flex-grow-1">
					<div className="fw-medium text-white mb-1">ClickUp Authorization</div>
					{popupBlocked ? (
						<div className="small" style={textMutedStyle}>
							Popup was blocked by your browser.
							<button type="button" className="btn btn-link p-0 text-white text-decoration-none ms-1" onClick={handleRetryPopup} style={{ fontSize: "inherit" }}>
								Click here to open again
							</button>
						</div>
					) : (
						<div className="small" style={textMutedStyle}>
							Please complete the ClickUp authorization in the new window that opened.
						</div>
					)}
				</div>
				<button type="button" className="btn-close btn-close-sm btn-close-white" onClick={() => setShowPopupMessage(false)} aria-label="Close" />
			</div>
		</div>
	);

	return (
		<div className="clickup-input-container">
			<div className="p-3 border rounded" style={cardStyle}>
				<div className="d-flex align-items-center justify-content-between d-none d-sm-flex">
					<div className="d-flex align-items-center gap-3">
						<div
							style={{
								width: 32,
								height: 32,
								borderRadius: "50%",
								overflow: "hidden",
								background: "#7B68EE",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
							}}>
							<img
								src={clickupLogo}
								alt="ClickUp logo"
								style={{
									width: "100%",
									height: "100%",
									objectFit: "contain",
								}}
							/>
						</div>
						<div>
							<div className="fw-medium text-white" style={{ fontSize: "0.95rem" }}>ClickUp Integration</div>
							<div className="small" style={textMutedStyle}>Connect your ClickUp account to access projects</div>
						</div>
					</div>
					<Button
						variant="primary"
						size="sm"
						onClick={handleConnectClickUp}
						disabled={isDisabled}
						className="clickup-connect-button"
						style={{
							display: "flex",
							alignItems: "center",
							gap: "6px",
							fontWeight: "500",
							padding: "6px 12px",
							borderRadius: "6px",
							fontSize: "0.875rem",
							transition: "all 0.2s ease",
						}}>
						{getButtonText()}
					</Button>
				</div>

				<div className="d-flex d-sm-none flex-column">
					<div className="d-flex align-items-center gap-3 mb-3">
						<div
							style={{
								width: 32,
								height: 32,
								borderRadius: "50%",
								overflow: "hidden",
								background: "#7B68EE",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
							}}>
							<img
								src={clickupLogo}
								alt="ClickUp logo"
								style={{
									width: "100%",
									height: "100%",
									objectFit: "contain",
								}}
							/>
						</div>
						<div>
							<div className="fw-medium text-white" style={{ fontSize: "0.95rem" }}>ClickUp Integration</div>
							<div className="small" style={textMutedStyle}>Connect your ClickUp account to access projects</div>
						</div>
					</div>
					<Button
						variant="primary"
						size="sm"
						onClick={handleConnectClickUp}
						disabled={isDisabled}
						className="clickup-connect-button"
						style={{
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							gap: "6px",
							fontWeight: "500",
							padding: "8px 16px",
							borderRadius: "6px",
							fontSize: "0.875rem",
							transition: "all 0.2s ease",
						}}>
						{getButtonText()}
					</Button>
				</div>
			</div>

			{popupMessage}

			{value === "connected" && (
				<div className="text-success mt-2 d-flex align-items-center gap-2" style={{ fontSize: "0.875rem" }}>
					<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
						<path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
					</svg>
					ClickUp successfully connected
				</div>
			)}

			{value === "connecting" && !showPopupMessage && (
				<div className="mt-2 d-flex align-items-center gap-2" style={{ fontSize: "0.875rem", color: "var(--color-text-secondary)" }}>
					<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
						<path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
					</svg>
					Please complete the authentication in the new window that opened.
				</div>
			)}
		</div>
	);
};

export default ClickUpInput;


