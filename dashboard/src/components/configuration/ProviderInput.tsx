import React, { useState, useEffect } from "react";
import { Button, Modal, Form, Spinner } from "react-bootstrap";
import { callApi } from "../../services/base_service";
import { setDataForKeyApi } from "../../services/project_services";
import { useToast } from "../../utils/toast_context";
import { ProviderConfig } from "./providerConfigs";

interface ProviderInputProps {
	config: ProviderConfig;
	value: string;
	onChange?: (value: string) => void;
	selectResources?: (inputData: any) => void;
	selectedResources?: any;
	inputData?: any;
	onRefresh?: () => void;
	highlightSelectResources?: boolean;
}

const ProviderInput: React.FC<ProviderInputProps> = ({
	config,
	value,
	onChange,
	selectResources,
	selectedResources,
	inputData,
	onRefresh,
	highlightSelectResources = false,
}) => {
	const [isLoading, setIsLoading] = useState(false);
	const [isSelectingResources, setIsSelectingResources] = useState(false);
	const [showManualModal, setShowManualModal] = useState(false);
	const [manualToken, setManualToken] = useState("");
	const [isSubmittingToken, setIsSubmittingToken] = useState(false);
	const [tokenValidationError, setTokenValidationError] = useState("");
	const [showPopupMessage, setShowPopupMessage] = useState(false);
	const [authUrl, setAuthUrl] = useState("");
	const [popupBlocked, setPopupBlocked] = useState(false);
	const { showToast } = useToast();

	const isOAuth = config.authType === "oauth";
	const isConfigured = value && value !== "" && value !== "null" && value !== "undefined";
	const selectedResourcesCount = Array.isArray(selectedResources) ? selectedResources.length : 0;

	useEffect(() => {
		if (showManualModal && isConfigured) {
			setManualToken(value);
			if (config.validateToken) {
				setTokenValidationError(config.validateToken(value));
			}
		}
	}, [showManualModal, value, isConfigured, config]);

	const handleManualTokenChange = (nextValue: string) => {
		setManualToken(nextValue);
		if (config.validateToken) {
			setTokenValidationError(config.validateToken(nextValue));
		}
	};

	const handleSelectResources = async () => {
		if (selectResources && inputData) {
			try {
				setIsSelectingResources(true);
				await selectResources(inputData);
			} catch (error) {
				console.error(`Error selecting ${config.displayName} resources:`, error);
			} finally {
				setIsSelectingResources(false);
			}
		}
	};

	const handleConnect = async () => {
		if (!isOAuth) {
			setShowManualModal(true);
			return;
		}

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
				provider_name: config.name,
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
						if (popup.closed) setPopupBlocked(true);
					}, 1000);
				}
			} else {
				throw new Error("No auth URL received from server");
			}
		} catch (error) {
			console.error(`Error initiating ${config.displayName} connection:`, error);
			showToast(`Failed to connect ${config.displayName}. Please try again.`, "danger");
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
		if (config.validateToken) {
			const validationError = config.validateToken(manualToken);
			setTokenValidationError(validationError);
			if (validationError) {
				return;
			}
		}

		try {
			setIsSubmittingToken(true);
			await setDataForKeyApi(manualToken, `${config.name}_access_token`, "string");
			showToast(`${config.displayName} token saved successfully!`, "success");

			if (onChange) onChange(manualToken);

			setShowManualModal(false);
			setManualToken("");

			if (onRefresh) await onRefresh();

			if (selectResources && inputData) {
				try {
					handleSelectResources();
				} catch (error) {
					console.error(`Error auto-selecting resources after token save:`, error);
				}
			}
		} catch (error) {
			console.error(`Error saving ${config.displayName} token:`, error);
			showToast(`Failed to save ${config.displayName} token. Please try again.`, "danger");
		} finally {
			setIsSubmittingToken(false);
		}
	};

	const ProviderIcon = () => (
		<div
			style={{
				width: 32,
				height: 32,
				borderRadius: "50%",
				overflow: "hidden",
				background: config.brandColor,
				display: "flex",
				alignItems: "center",
				justifyContent: "center",
				color: "#fff",
				fontWeight: 700,
				fontSize: config.iconLetter && config.iconLetter.length > 1 ? "0.65rem" : "0.9rem",
				flexShrink: 0,
				letterSpacing: "-0.02em",
			}}>
			{config.iconImage ? (
				<img
					src={config.iconImage}
					alt={`${config.displayName} logo`}
					style={{
						width: "95%",
						height: "95%",
						objectFit: "cover",
					}}
				/>
			) : (
				config.iconLetter || config.displayName[0]
			)}
		</div>
	);

	const connectButtonLabel = isOAuth ? `Connect ${config.displayName}` : `Enter ${config.manualTokenLabel || "Token"}`;
	const reconnectButtonLabel = isOAuth ? "Reconnect" : "Update Token";

	const manualTokenModal = (
		<Modal
			show={showManualModal}
			onHide={() => {
				setShowManualModal(false);
				setManualToken("");
				setTokenValidationError("");
			}}
			centered>
			<Modal.Header closeButton>
				<Modal.Title>
					Enter {config.displayName} {config.manualTokenLabel || "Access Token"}
				</Modal.Title>
			</Modal.Header>
			<Modal.Body>
				<Form.Group>
					<Form.Label className="text-white mb-2">{config.manualTokenLabel || `${config.displayName} Access Token`}</Form.Label>
					<Form.Control
						type="text"
						placeholder={config.manualTokenPlaceholder || "Enter token..."}
						value={manualToken}
						autoComplete="off"
						onChange={(e) => handleManualTokenChange(e.target.value)}
						autoFocus
						isInvalid={!!tokenValidationError}
					/>
					{tokenValidationError && (
						<Form.Control.Feedback type="invalid" style={{ display: "block" }}>
							{tokenValidationError}
						</Form.Control.Feedback>
					)}
					{config.manualTokenHelp && (
						<p className="text-white mt-2 small">
							{config.manualTokenHelp}{" "}
							{config.manualTokenHelpLinkText && config.manualTokenHelpLinkUrl && (
								<a className="text-white" href={config.manualTokenHelpLinkUrl} target="_blank" rel="noreferrer">
									{config.manualTokenHelpLinkText}
								</a>
							)}
						</p>
					)}
				</Form.Group>
			</Modal.Body>
			<Modal.Footer>
				<Button
					variant="secondary"
					onClick={() => {
						setShowManualModal(false);
						setManualToken("");
						setTokenValidationError("");
					}}
					disabled={isSubmittingToken}>
					Cancel
				</Button>
				<Button
					variant="primary"
					onClick={handleManualTokenSubmit}
					disabled={!manualToken.trim() || !!tokenValidationError || isSubmittingToken}>
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
					<div className="fw-medium text-white mb-1">{config.displayName} Authorization</div>
					{popupBlocked ? (
						<div className="small" style={{ color: "#A1A1AA" }}>
							Popup was blocked by your browser.
							<button
								className="btn btn-link p-0 text-white text-decoration-none ms-1"
								onClick={handleRetryPopup}
								style={{ fontSize: "inherit" }}>
								Click here to open again
							</button>
						</div>
					) : (
						<div className="small" style={{ color: "#A1A1AA" }}>
							Please complete the {config.displayName} authorization in the new window.
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
				<div className="provider-input-container">
					<div className="p-3 border rounded" style={{ backgroundColor: "#1C1F28", borderColor: "#2D313A" }}>
						<div className="d-flex align-items-center justify-content-between flex-wrap gap-3">
							<div className="d-flex align-items-center gap-3">
								<ProviderIcon />
								<div>
									<div className="fw-medium text-white" style={{ fontSize: "0.95rem" }}>
										{config.displayName} Integration
									</div>
									<div className="text-success small d-flex align-items-center gap-1">
										<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
											<path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
										</svg>
										Connected to {config.displayName}
									</div>
									{selectedResourcesCount > 0 && (
										<div className="small" style={{ color: "#A1A1AA" }}>
											{selectedResourcesCount} {config.selectResourcesLabel?.toLowerCase().replace("select ", "") || "resources"} selected
										</div>
									)}
								</div>
							</div>
							<div className="d-flex flex-column align-items-end gap-1">
								<div className="d-flex gap-2">
									{config.hasSelectResources && (
										<Button
											variant="primary"
											size="sm"
											onClick={handleSelectResources}
											disabled={isSelectingResources}
											className={highlightSelectResources ? "highlight-pulse" : ""}
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
											{isSelectingResources ? (
												<>
													<span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
													Loading...
												</>
											) : (
												<>
													{config.selectResourcesLabel || "Select Resources"}
													{selectedResourcesCount > 0 && (
														<span className="badge bg-dark text-white ms-1" style={{ fontSize: "0.75rem" }}>
															{selectedResourcesCount}
														</span>
													)}
												</>
											)}
										</Button>
									)}
									<Button
										variant="outline-success"
										size="sm"
										onClick={handleConnect}
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
										{reconnectButtonLabel}
									</Button>
								</div>
								{config.hasManualToken && isOAuth && (
									<a
										href="#"
										onClick={(e) => {
											e.preventDefault();
											setShowManualModal(true);
										}}
										style={{ fontSize: "0.75rem", color: "#A1A1AA", textDecoration: "none" }}
										onMouseEnter={(e) => (e.currentTarget.style.textDecoration = "underline")}
										onMouseLeave={(e) => (e.currentTarget.style.textDecoration = "none")}>
										or manually update token
									</a>
								)}
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
							inset: 0,
							backgroundColor: "rgba(0, 0, 0, 0.5)",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							zIndex: 9999,
						}}>
						<div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.75rem" }}>
							<Spinner animation="border" role="status" variant="light" style={{ width: "1.5rem", height: "1.5rem" }}>
								<span className="visually-hidden">Loading...</span>
							</Spinner>
							<p className="text-white mb-0" style={{ fontSize: "0.9rem", fontWeight: 500 }}>
								Fetching resources...
							</p>
						</div>
					</div>
				)}
			</>
		);
	}

	return (
		<>
			<div className="provider-input-container">
				<div className="p-3 border rounded" style={{ backgroundColor: "#1C1F28", borderColor: "#2D313A" }}>
					<div className="d-flex align-items-center justify-content-between flex-wrap gap-3">
						<div className="d-flex align-items-center gap-3">
							<ProviderIcon />
							<div>
								<div className="fw-medium text-white" style={{ fontSize: "0.95rem" }}>
									{config.displayName} Integration
								</div>
								<div className="small" style={{ color: "#A1A1AA" }}>
									{config.description}
								</div>
							</div>
						</div>
						<div className="d-flex flex-column align-items-end gap-1">
							<Button
								variant="primary"
								size="sm"
								onClick={handleConnect}
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
								{isLoading ? "Connecting..." : connectButtonLabel}
							</Button>
							{config.hasManualToken && isOAuth && (
								<a
									href="#"
									onClick={(e) => {
										e.preventDefault();
										setShowManualModal(true);
									}}
									style={{ fontSize: "0.75rem", color: "#A1A1AA", textDecoration: "none" }}
									onMouseEnter={(e) => (e.currentTarget.style.textDecoration = "underline")}
									onMouseLeave={(e) => (e.currentTarget.style.textDecoration = "none")}>
									or manually enter your token
								</a>
							)}
						</div>
					</div>
				</div>
			</div>
			{popupMessage}
			{manualTokenModal}
		</>
	);
};

export default ProviderInput;
