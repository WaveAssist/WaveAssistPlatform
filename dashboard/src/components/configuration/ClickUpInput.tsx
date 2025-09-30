import React, { useState, useEffect } from "react";
import { Button } from "react-bootstrap";
import { callApi } from "../../services/base_service";

interface ClickUpInputProps {
	value: string;
	selectResources?: (inputData: any) => void;
	inputData?: any;
}

const ClickUpInput: React.FC<ClickUpInputProps> = ({ value, selectResources, inputData }) => {
	const [isLoading, setIsLoading] = useState(false);
	const [isSelectingResources, setIsSelectingResources] = useState(false);

	const handleSelectResources = async () => {
		if (selectResources && inputData) {
			try {
				setIsSelectingResources(true);
				await selectResources(inputData);
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
				window.open(response.auth_url, "_blank");
			} else {
				throw new Error("No auth URL received from server");
			}
		} catch (error) {
			console.error("Error initiating ClickUp connection:", error);
			alert("Failed to initiate ClickUp connection. Please try again.");
		} finally {
			setIsLoading(false);
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

	if (isConfigured && value !== "connecting") {
		return (
			<div className="clickup-input-container">
				<div className="p-3 border rounded" style={{ backgroundColor: "#f8f9fa", borderColor: "#e9ecef" }}>
					<div className="d-flex align-items-center justify-content-between d-none d-sm-flex">
						<div className="d-flex align-items-center gap-3">
							{/* ClickUp icon (simple checkmark in a square as placeholder) */}
							<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0 }}>
								<path d="M3 3h18v18H3z" fill="#7b68ee"/>
								<path d="M9 12.5l2 2 4-4" stroke="#fff" strokeWidth="2" fill="none"/>
							</svg>
							<div>
								<div className="fw-medium" style={{ fontSize: "0.95rem" }}>ClickUp Integration</div>
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
							<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0 }}>
								<path d="M3 3h18v18H3z" fill="#7b68ee"/>
								<path d="M9 12.5l2 2 4-4" stroke="#fff" strokeWidth="2" fill="none"/>
							</svg>
							<div>
								<div className="fw-medium" style={{ fontSize: "0.95rem" }}>ClickUp Integration</div>
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

	return (
		<div className="clickup-input-container">
			<div className="p-3 border rounded" style={{ backgroundColor: "#f8f9fa", borderColor: "#e9ecef" }}>
				<div className="d-flex align-items-center justify-content-between d-none d-sm-flex">
					<div className="d-flex align-items-center gap-3">
						<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0 }}>
							<path d="M3 3h18v18H3z" fill="#7b68ee"/>
							<path d="M9 12.5l2 2 4-4" stroke="#fff" strokeWidth="2" fill="none"/>
						</svg>
						<div>
							<div className="fw-medium" style={{ fontSize: "0.95rem" }}>ClickUp Integration</div>
							<div className="text-muted small">Connect your ClickUp account to access projects</div>
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
						<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0 }}>
							<path d="M3 3h18v18H3z" fill="#7b68ee"/>
							<path d="M9 12.5l2 2 4-4" stroke="#fff" strokeWidth="2" fill="none"/>
						</svg>
						<div>
							<div className="fw-medium" style={{ fontSize: "0.95rem" }}>ClickUp Integration</div>
							<div className="text-muted small">Connect your ClickUp account to access projects</div>
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

			{value === "connected" && (
				<div className="text-success mt-2 d-flex align-items-center gap-2" style={{ fontSize: "0.875rem" }}>
					<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
						<path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
					</svg>
					ClickUp successfully connected
				</div>
			)}

			{value === "connecting" && (
				<div className="text-info mt-2 d-flex align-items-center gap-2" style={{ fontSize: "0.875rem" }}>
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


