import React, { useState, useEffect } from "react";
import { Button, Modal, Form, Spinner } from "react-bootstrap";
import { callApi } from "../../services/base_service";
import { setDataForKeyApi } from "../../services/project_services";
import { useToast } from "../../utils/toast_context";

interface GitHubInputProps {
	value: string;
	onChange?: (value: string) => void;
	selectResources?: (inputData: any) => void;
	selectedResources?: any;
	inputData?: any;
	onRefresh?: () => void;
	highlightSelectResources?: boolean;
}

const GitHubInput: React.FC<GitHubInputProps> = ({
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

	const validateGitHubToken = (token: string): string => {
		if (!token) {
			return "";
		}

		// Define token types with their prefixes and expected lengths
		const tokenTypes = [
			{ prefix: "ghp_", length: 40, name: "Personal Access Token (Classic)" },
			{ prefix: "gho_", length: 40, name: "OAuth Access Token" },
			{ prefix: "github_pat_", length: 93, name: "Fine-Grained Personal Access Token" },
			{ prefix: "ghu_", length: 40, name: "GitHub App User-to-Server Token" },
			{ prefix: "ghs_", length: 40, name: "GitHub App Server-to-Server Token" },
			{ prefix: "ghr_", length: 40, name: "GitHub App Refresh Token" },
		];

		// Check if token matches any known type
		const matchingType = tokenTypes.find((type) => token.startsWith(type.prefix));

		if (!matchingType) {
			return `Please enter a valid GitHub Access Token`;
		}

		// Check length for the specific token type
		if (token.length !== matchingType.length) {
			return `Please enter a valid GitHub Access Token`;
		}

		return "";
	};

	const handleTokenChange = (value: string) => {
		setManualToken(value);
		const error = validateGitHubToken(value);
		setTokenValidationError(error);
	};

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
				console.error("Error selecting resources:", error);
			} finally {
				setIsSelectingResources(false);
			}
		}
	};

	const handleConnectGitHub = async () => {
		try {
			setIsLoading(true);
			setPopupBlocked(false);
			setShowPopupMessage(false);

			const uid = localStorage.getItem("uid");
			const projectKey = localStorage.getItem("selected_project_key");

			if (!uid || !projectKey) {
				throw new Error("Missing user ID or project key");
			}

			// Call the providers/initiate/ API
			const body = new URLSearchParams({
				uid: uid,
				project_key: projectKey,
				provider_name: "github",
			});

			const response = await callApi("providers/initiate/", body);

			if (response && response.auth_url) {
				// Store the auth URL for potential retry
				setAuthUrl(response.auth_url);

				// Open the auth URL in a new window/tab
				const popup = window.open(response.auth_url, "_blank");

				// Check if popup was blocked
				if (!popup || popup.closed || typeof popup.closed == "undefined") {
					// Popup was blocked
					setPopupBlocked(true);
					setShowPopupMessage(true);
				} else {
					// Popup opened successfully
					setShowPopupMessage(true);

					// Check if popup is still open after a short delay
					setTimeout(() => {
						if (popup.closed) {
							// Popup was closed quickly, might have been blocked
							setPopupBlocked(true);
						}
					}, 1000);
				}
			} else {
				throw new Error("No auth URL received from server");
			}
		} catch (error) {
			console.error("Error initiating GitHub connection:", error);
			alert("Failed to initiate GitHub connection. Please try again.");
		} finally {
			setIsLoading(false);
		}
	};

	const handleRetryPopup = () => {
		if (authUrl) {
			const popup = window.open(authUrl, "_blank");
			if (!popup || popup.closed || typeof popup.closed == "undefined") {
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
			console.log("Manual GitHub Token:", manualToken);

			await setDataForKeyApi(manualToken, "github_access_token", "string");
			showToast("GitHub token saved successfully!", "success");

			// Call onChange with the new token value
			if (onChange) {
				onChange(manualToken);
			}

			setShowManualModal(false);
			setManualToken("");

			// Trigger refresh to reload wizard inputs and show connected state
			if (onRefresh) {
				await onRefresh();
			}

			// Automatically trigger resource selection after token is saved
			if (selectResources && inputData) {
				try {
					handleSelectResources();
				} catch (error) {
					console.error("Error auto-selecting resources after token save:", error);
					// Error is already handled by the parent component with a toast
				}
			}
		} catch (error) {
			console.error("Error saving GitHub token:", error);
			showToast("Failed to save GitHub token. Please try again.", "danger");
		} finally {
			setIsSubmittingToken(false);
		}
	};

	const isDisabled = isLoading;

	// Check if GitHub is already configured (value is not empty, null, or undefined)
	const isConfigured = value && value !== "" && value !== "null" && value !== "undefined";

	// Get selected resources count
	const selectedResourcesCount = Array.isArray(selectedResources) ? selectedResources.length : 0;

	// Manual Token Entry Modal - shared between both states
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
				<Modal.Title>Enter GitHub Access Token</Modal.Title>
			</Modal.Header>
			<Modal.Body>
				<Form.Group>
					<Form.Label className="text-white mb-2">GitHub Access Token</Form.Label>
					<Form.Control
						type="text"
						placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
						value={manualToken}
						autoComplete="off"
						onChange={(e) => handleTokenChange(e.target.value)}
						autoFocus
						isInvalid={!!tokenValidationError}
					/>
					{tokenValidationError && (
						<Form.Control.Feedback type="invalid" style={{ display: "block" }}>
							{tokenValidationError}
						</Form.Control.Feedback>
					)}
					<p className="text-white mt-2 small">
						Enter your GitHub Access Token.{" "}
						<a className="text-white" href="https://waveassist.io/blog/how-to-get-your-github-token-for-gitzoid" target="_blank">
							How to find?
						</a>
					</p>
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
				<Button variant="primary" onClick={handleManualTokenSubmit} disabled={!manualToken.trim() || !!tokenValidationError || isSubmittingToken}>
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

	// Popup Message Component
	const popupMessage = showPopupMessage && (
		<div className="mt-3 p-3 border rounded" style={{ backgroundColor: "#1a2332", borderColor: "#0d6efd" }}>
			<div className="d-flex align-items-center gap-2">
				<svg width="20" height="20" viewBox="0 0 24 24" fill="#0d6efd">
					<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
				</svg>
				<div className="flex-grow-1">
					<div className="fw-medium text-white mb-1">GitHub Authorization</div>
					{popupBlocked ? (
						<div className="small" style={{ color: "#adb5bd" }}>
							Popup was blocked by your browser.
							<button className="btn btn-link p-0 text-white text-decoration-none ms-1" onClick={handleRetryPopup} style={{ fontSize: "inherit" }}>
								Click here to open again
							</button>
						</div>
					) : (
						<div className="small" style={{ color: "#adb5bd" }}>
							Please continue the GitHub authorization flow in the new window that opened.
						</div>
					)}
				</div>
				<button className="btn-close btn-close-sm btn-close-white" onClick={() => setShowPopupMessage(false)} aria-label="Close"></button>
			</div>
		</div>
	);

	// If GitHub is already configured, show the configured state
	if (isConfigured) {
		return (
			<>
				<div className="github-input-container">
					<div className="p-3 border rounded" style={{ backgroundColor: "#f8f9fa", borderColor: "#e9ecef" }}>
						{/* Desktop layout: horizontal with buttons on the right */}
						<div className="d-flex align-items-center justify-content-between d-none d-sm-flex">
							<div className="d-flex align-items-center gap-3">
								{/* GitHub icon */}
								<svg width="24" height="24" viewBox="0 0 24 24" fill="white" style={{ flexShrink: 0 }}>
									<path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
								</svg>
								<div>
									<div className="fw-medium" style={{ fontSize: "0.95rem" }}>
										GitHub Integration
									</div>
									<div className="text-success small d-flex align-items-center gap-1">
										<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
											<path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
										</svg>
										Connected to GitHub
									</div>
								</div>
							</div>
							<div className="d-flex flex-column align-items-end gap-1">
								<div className="d-flex gap-2">
									<Button
										variant="primary"
										size="sm"
										onClick={handleSelectResources}
										disabled={isSelectingResources}
										className={`github-action-button ${highlightSelectResources ? "highlight-pulse" : ""}`}
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
											<>
												Select Resources
												{selectedResourcesCount > 0 && (
													<span className="badge bg-dark text-white ms-1" style={{ fontSize: "0.75rem" }}>
														{selectedResourcesCount}
													</span>
												)}
											</>
										)}
									</Button>

									<Button
										variant="outline-success"
										size="sm"
										onClick={handleConnectGitHub}
										className="github-action-button"
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
								<a
									href="#"
									onClick={(e) => {
										e.preventDefault();
										setShowManualModal(true);
									}}
									style={{
										fontSize: "0.75rem",
										color: "#6c757d",
										textDecoration: "none",
									}}
									onMouseEnter={(e) => (e.currentTarget.style.textDecoration = "underline")}
									onMouseLeave={(e) => (e.currentTarget.style.textDecoration = "none")}>
									or manually update token
								</a>
							</div>
						</div>

						{/* Mobile layout: vertical stack */}
						<div className="d-flex d-sm-none flex-column">
							{/* GitHub info section */}
							<div className="d-flex align-items-center gap-3 mb-3">
								{/* GitHub icon */}
								<svg width="24" height="24" viewBox="0 0 24 24" fill="white" style={{ flexShrink: 0 }}>
									<path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
								</svg>
								<div>
									<div className="fw-medium" style={{ fontSize: "0.95rem" }}>
										GitHub Integration
									</div>
									<div className="text-success small d-flex align-items-center gap-1">
										<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
											<path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
										</svg>
										Connected to GitHub
									</div>
								</div>
							</div>

							{/* Buttons section - stacked on mobile */}
							<div className="d-flex flex-column gap-2">
								<Button
									variant="primary"
									size="sm"
									onClick={handleSelectResources}
									disabled={isSelectingResources}
									className={`github-action-button ${highlightSelectResources ? "highlight-pulse" : ""}`}
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
										<>
											Select Resources
											{selectedResourcesCount > 0 && (
												<span className="badge bg-dark text-white ms-1" style={{ fontSize: "0.75rem" }}>
													{selectedResourcesCount}
												</span>
											)}
										</>
									)}
								</Button>

								<Button
									variant="outline-success"
									size="sm"
									onClick={handleConnectGitHub}
									className="github-action-button"
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

								{/* Manual token update link - centered on mobile */}
								<div className="text-center">
									<a
										href="#"
										onClick={(e) => {
											e.preventDefault();
											setShowManualModal(true);
										}}
										style={{
											fontSize: "0.75rem",
											color: "#6c757d",
											textDecoration: "none",
										}}
										onMouseEnter={(e) => (e.currentTarget.style.textDecoration = "underline")}
										onMouseLeave={(e) => (e.currentTarget.style.textDecoration = "none")}>
										or update token manually
									</a>
								</div>
							</div>
						</div>
					</div>
				</div>
				{popupMessage}
				{manualTokenModal}
			</>
		);
	}

	// Default state - show connect button
	return (
		<>
			<div className="github-input-container">
				<div className="p-3 border rounded" style={{ backgroundColor: "#f8f9fa", borderColor: "#e9ecef" }}>
					{/* Desktop layout: horizontal with button on the right */}
					<div className="d-flex align-items-center justify-content-between d-none d-sm-flex">
						<div className="d-flex align-items-center gap-3">
							{/* GitHub icon */}
							<svg width="24" height="24" viewBox="0 0 24 24" fill="white" style={{ flexShrink: 0 }}>
								<path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
							</svg>
							<div>
								<div className="fw-medium" style={{ fontSize: "0.95rem" }}>
									GitHub Integration
								</div>
								<div className="text-muted small">Connect your GitHub account to access repositories</div>
							</div>
						</div>
						<div className="d-flex flex-column align-items-end gap-1">
							<Button
								variant="primary"
								size="sm"
								onClick={handleConnectGitHub}
								disabled={isDisabled}
								className="github-connect-button"
								style={{
									display: "flex",
									alignItems: "center",
									gap: "6px",
									fontWeight: "600",
									padding: "6px 24px",
									borderRadius: "6px",
									fontSize: "0.875rem",
									transition: "all 0.2s ease",
								}}>
								{isLoading ? "Connecting..." : "Connect GitHub"}
							</Button>
							<a
								href="#"
								onClick={(e) => {
									e.preventDefault();
									setShowManualModal(true);
								}}
								style={{
									fontSize: "0.75rem",
									color: "#6c757d",
									textDecoration: "none",
								}}
								onMouseEnter={(e) => (e.currentTarget.style.textDecoration = "underline")}
								onMouseLeave={(e) => (e.currentTarget.style.textDecoration = "none")}>
								or manually enter your token
							</a>
						</div>
					</div>

					{/* Mobile layout: vertical stack */}
					<div className="d-flex d-sm-none flex-column">
						{/* GitHub info section */}
						<div className="d-flex align-items-center gap-3 mb-3">
							{/* GitHub icon */}
							<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0 }}>
								<path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
							</svg>
							<div>
								<div className="fw-medium" style={{ fontSize: "0.95rem" }}>
									GitHub Integration
								</div>
								<div className="text-muted small">Connect your GitHub account to access repositories</div>
							</div>
						</div>

						{/* Connect button - full width on mobile */}
						<Button
							variant="primary"
							size="sm"
							onClick={handleConnectGitHub}
							disabled={isDisabled}
							className="github-connect-button"
							style={{
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								gap: "6px",
								fontWeight: "600",
								padding: "8px 24px",
								borderRadius: "6px",
								fontSize: "0.875rem",
								transition: "all 0.2s ease",
							}}>
							{isLoading ? "Connecting..." : "Connect GitHub"}
						</Button>

						{/* Manual entry link - centered on mobile */}
						<div className="text-center mt-2">
							<a
								href="#"
								onClick={(e) => {
									e.preventDefault();
									setShowManualModal(true);
								}}
								style={{
									fontSize: "0.75rem",
									color: "#6c757d",
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

			{/* Loading Overlay */}
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
					<p className="text-white mt-3" style={{ fontSize: "1.1rem", fontWeight: "500" }}>
						Fetching resources...
					</p>
				</div>
			)}
		</>
	);
};

export default GitHubInput;
