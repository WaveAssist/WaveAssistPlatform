import React, { useState, useEffect } from "react";
import { Button, Modal, Form, Spinner } from "react-bootstrap";
import { callApi } from "../../services/base_service";
import { setDataForKeyApi } from "../../services/project_services";
import { useToast } from "../../utils/toast_context";

interface GitHubInputProps {
	value: string;
	selectResources?: (inputData: any) => void;
	inputData?: any;
	onRefresh?: () => void;
}

const GitHubInput: React.FC<GitHubInputProps> = ({ value, selectResources, inputData, onRefresh }) => {
	const [isLoading, setIsLoading] = useState(false);
	const [isSelectingResources, setIsSelectingResources] = useState(false);
	const [showManualModal, setShowManualModal] = useState(false);
	const [manualToken, setManualToken] = useState("");
	const [isSubmittingToken, setIsSubmittingToken] = useState(false);
	const [tokenValidationError, setTokenValidationError] = useState("");
	const { showToast } = useToast();

	const validateGitHubToken = (token: string): string => {
		if (!token) {
			return "";
		}

		// Check if token starts with ghp_ or gho_
		if (!token.startsWith("ghp_") && !token.startsWith("gho_")) {
			return "Token must start with 'ghp_' or 'gho_'";
		}

		// GitHub tokens are 40 characters total
		if (token.length !== 40) {
			return "Token must be exactly 40 characters long";
		}

		return "";
	};

	const handleTokenChange = (value: string) => {
		setManualToken(value);
		const error = validateGitHubToken(value);
		setTokenValidationError(error);
	};

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

	// Monitor value prop changes and automatically trigger resource selection when connected
	useEffect(() => {
		if (value === "connected" && selectResources && inputData) {
			// Automatically trigger resource selection when GitHub connection is successful
			handleSelectResources();
		}
	}, [value, selectResources, inputData]);

	const handleConnectGitHub = async () => {
		try {
			setIsLoading(true);

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
				// Open the auth URL in a new window/tab
				window.open(response.auth_url, "_blank");
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

	const handleManualTokenSubmit = async () => {
		try {
			setIsSubmittingToken(true);
			console.log("Manual GitHub Token:", manualToken);

			await setDataForKeyApi(manualToken, "github_access_token", "string");
			showToast("GitHub token saved successfully!", "success");
			setShowManualModal(false);
			setManualToken("");

			// Trigger refresh to reload wizard inputs and show connected state
			if (onRefresh) {
				await onRefresh();
			}

			// Automatically trigger resource selection after token is saved
			if (selectResources && inputData) {
				try {
					await selectResources(inputData);
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

	const getButtonText = () => {
		if (isLoading) return "Connecting...";
		if (value === "connecting") return "Connecting to GitHub...";
		if (value === "connected") return "Connected to GitHub";
		return "Connect GitHub";
	};

	const isDisabled = isLoading || value === "connecting" || value === "connected";

	// Check if GitHub is already configured (value is not empty, null, or undefined)
	const isConfigured = value && value !== "" && value !== "null" && value !== "undefined";

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
				<Modal.Title>Enter GitHub Personal Access Token</Modal.Title>
			</Modal.Header>
			<Modal.Body>
				<Form.Group className="mx-3">
					<Form.Label className="text-white mt-4 mb-2">GitHub Personal Access Token (GHP)</Form.Label>
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
						Enter your GitHub Personal Access Token.{" "}
						<a className="text-white" href="https://gitzoid.com/blog/how-to-get-your-github-token-for-gitzoid-fine-grained-classic" target="_blank">
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

	// If GitHub is already configured, show the configured state
	if (isConfigured && value !== "connecting") {
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
									{isSelectingResources ? (
										<>
											<span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
											Loading...
										</>
									) : (
										"Select Resources"
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
								{isSelectingResources ? (
									<>
										<span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
										Loading...
									</>
								) : (
									"Select Resources"
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
									or update manual token
								</a>
							</div>
						</div>
					</div>
				</div>
			</div>
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
								fontWeight: "500",
								padding: "6px 12px",
								borderRadius: "6px",
								fontSize: "0.875rem",
								transition: "all 0.2s ease",
							}}>
							{getButtonText()}
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
							or manually enter your GHP
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
							fontWeight: "500",
							padding: "8px 16px",
							borderRadius: "6px",
							fontSize: "0.875rem",
							transition: "all 0.2s ease",
						}}>
						{getButtonText()}
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
							or manually enter your GHP
						</a>
					</div>
				</div>
			</div>
		</div>

			{value === "connected" && (
				<div className="text-success mt-2 d-flex align-items-center gap-2" style={{ fontSize: "0.875rem" }}>
					<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
						<path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
					</svg>
					GitHub successfully connected
				</div>
			)}

			{value === "connecting" && (
				<div className="text-info mt-2 d-flex align-items-center gap-2" style={{ fontSize: "0.875rem" }}>
					<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
						<path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z" />
					</svg>
					Please complete the authentication in the new window that opened.
				</div>
			)}

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
