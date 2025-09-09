import React, { useEffect, useState } from "react";
import { usePostHog } from "posthog-js/react";
import { useToast } from "../utils/toast_context";
import { useRefresh } from "../utils/RefreshContext";
import { Button, Form, Spinner, Modal } from "react-bootstrap";
import { fetchTemplateApi, setDataForKeyApi, runDAGApi } from "../services/project_services";
import { deployProjectApi } from "../services/navbar_services";
import { fetchRunningDeploymentApi, stopDeploymentApi } from "../services/deployment_services";
import { useNavigate } from "react-router-dom";
import InputFactory from "./configuration/InputFactory";
import "./assistant_component.css";

const AssistantComponent: React.FC = () => {
	const { showToast } = useToast();
	const { shouldRefresh } = useRefresh();
	const posthog = usePostHog();
	const navigate = useNavigate();

	// Get user name from localStorage
	const userData = JSON.parse(localStorage.getItem("user_data") || "{}");
	const userName = userData.name || "User";

	// Wizard state
	const [wizardInputs, setWizardInputs] = useState<any[]>([]);
	const [wizardValues, setWizardValues] = useState<Record<string, string>>({});
	const [processingWizard, setProcessingWizard] = useState(false);
	const [wizardLoading, setWizardLoading] = useState(false);
	const [startingNodeKey] = useState<string | null>(null);
	const [runningDeploymentInfo, setRunningDeploymentInfo] = useState<any | null>(null);
	const [isRunning, setIsRunning] = useState(false);
	const [displayText, setDisplayText] = useState("");
	const [showConfigOverride, setShowConfigOverride] = useState(false);
	const [showStopConfirmation, setShowStopConfirmation] = useState(false);
	const [showReconfigureConfirmation, setShowReconfigureConfirmation] = useState(false);

	const fetch_wizard_inputs = async (template_key: string) => {
		setWizardLoading(true);
		try {
			const template_data = await fetchTemplateApi(template_key);
			const input_array = template_data.input_array;
			setWizardInputs(input_array);
			const defaults: Record<string, string> = {};
			input_array.forEach((i: any) => {
				if (i.default_value !== undefined) {
					defaults[i.key] = i.default_value;
				} else if (Array.isArray(i.options) && i.options.length > 0) {
					defaults[i.key] = i.options[0];
				} else {
					defaults[i.key] = "";
				}
			});
			setWizardValues(defaults);
		} catch (err) {
			console.error("Error fetching assistant:", err);
			showToast("Could not find anything to configure.", "warning");
		} finally {
			setWizardLoading(false);
		}
	};

	useEffect(() => {
		// Pageview context for assistant page
		try {
			posthog?.capture("$pageview", {
				page_category: "assistant",
				project_id: localStorage.getItem("selected_project_key") || undefined,
				environment: localStorage.getItem("selected_env_key") || undefined,
			});
		} catch (_err) {}
	}, []);

	// Fetch running deployment info
	const fetchRunning = async () => {
		try {
			const response = await fetchRunningDeploymentApi();
			setRunningDeploymentInfo(response);
			setIsRunning(true);
			setDisplayText(response.dag_object.schedule.display_text);
		} catch (err) {
			setIsRunning(false);
			setRunningDeploymentInfo(null);
			setDisplayText("");
		}
	};

	useEffect(() => {
		// Get template key and fetch wizard inputs
		const projectData = JSON.parse(localStorage.getItem("selected_project") || "{}");
		let templateKeyValue = projectData.template_key || localStorage.getItem("template_key") || "";

		if (templateKeyValue === "") {
			// Determine template key based on project type
			if (projectData.project_key?.includes("wavepredict")) {
				templateKeyValue = "wavepredict_template";
			} else if (projectData.project_key?.includes("patternanalyser")) {
				templateKeyValue = "patternanalyser-template";
			} else if (projectData.project_key?.includes("sentimentradar")) {
				templateKeyValue = "sentimentradar-template";
			} else {
				templateKeyValue = "default_template";
			}
		}
		fetch_wizard_inputs(templateKeyValue);
		fetchRunning();
	}, [shouldRefresh]);

	const handleWizardInputChange = (key: string, value: string) => {
		setWizardValues((prev) => ({ ...prev, [key]: value }));
	};

	const handleRunAndDeploy = async () => {
		// Validate that all required inputs have values
		const emptyInputs = wizardInputs.filter((input) => {
			const value = wizardValues[input.key];
			// Check if value is empty, null, undefined, or just whitespace
			return !value || value.trim() === "";
		});

		if (emptyInputs.length > 0) {
			showToast("Please provide input values for all required fields", "warning");
			return;
		}

		setProcessingWizard(true);
		try {
			for (const input of wizardInputs) {
				await setDataForKeyApi(wizardValues[input.key], input.key, "string");
			}
			const env = localStorage.getItem("selected_env_key") || "";
			console.log("Running DAB with starting node key: ", startingNodeKey, "and env: ", env);
			await runDAGApi(null, env);

			var version_code_string = `0.${Math.floor(Math.random() * 101)}.${Math.floor(Math.random() * 101)}`;
			console.log("Deploying project with version code: ", version_code_string);
			await deployProjectApi(version_code_string);
			// Switch UI to running state and fetch latest running info
			try {
				const response = await fetchRunningDeploymentApi();
				setRunningDeploymentInfo(response);
				setIsRunning(true);
				setDisplayText(response.dag_object.schedule.display_text);
				setShowConfigOverride(false);
			} catch (_fetchErr) {
				// Even if fetch fails, assume running state after successful deploy
				setIsRunning(true);
				setShowConfigOverride(false);
			}
		} catch (error) {
			console.error("Wizard run failed:", error);
			showToast("" + error, "danger");
		} finally {
			setProcessingWizard(false);
		}
	};

	const handleStopDeployment = async () => {
		try {
			const deploymentKey = runningDeploymentInfo?.deployment_object.key || "";
			if (!deploymentKey) {
				showToast("Could not determine deployment to stop.", "warning");
				return;
			}
			await stopDeploymentApi(deploymentKey);
			setIsRunning(false);
			setRunningDeploymentInfo(null);
			setDisplayText("");
			showToast("Schedule stopped successfully", "success");
		} catch (err) {
			console.error("Failed to stop:", err);
			showToast("Failed to stop. Please try again.", "danger");
		} finally {
			setShowStopConfirmation(false);
		}
	};

	const handleReconfigure = () => {
		setShowConfigOverride(true);
		setShowReconfigureConfirmation(false);
	};

	return (
		<div className="main-container assistant-container">
			<div className="mt-3 d-flex flex-column" style={{ height: "100%" }}>
				{/* Header */}
				<div className="assistant-header">
					<h3 className="assistant-title">Welcome, {userName}!</h3>
				</div>

				{/* Configuration Section */}
				{(!isRunning || showConfigOverride) && (
					<div className="row">
						{/* Configuration Card */}
						<div className="col-md-12">
							<div className="assistant-config-card">
								<div className="assistant-config-header">
									<h5 className="assistant-config-title">Setup Assistant</h5>
								</div>

								<div className="assistant-config-content">
									{wizardLoading ? (
										<div className="text-center">
											<Spinner animation="border" role="status" variant="success">
												<span className="visually-hidden">Loading...</span>
											</Spinner>
											<p className="text-muted mt-3">Loading configuration...</p>
										</div>
									) : (
										<>
											{wizardInputs.length === 0 ? (
												<div className="text-center py-4">
													<div className="mb-3">
														<i className="bi bi-check-circle-fill text-success" style={{ fontSize: "3rem" }}></i>
													</div>
													<h5 className="mb-3">Ready to run!</h5>
													<p className="text-muted mb-0">Your agent is ready to go. No additional configuration is needed.</p>
												</div>
											) : (
												<Form>
													{wizardInputs.map((input_dict) => (
														<InputFactory
															key={input_dict.key}
															inputConfig={input_dict}
															value={wizardValues[input_dict.key] || ""}
															onChange={(value) => handleWizardInputChange(input_dict.key, value)}
														/>
													))}
												</Form>
											)}
										</>
									)}
								</div>

								<div className="assistant-config-footer">
									<Button className="assistant-deploy-button" onClick={handleRunAndDeploy} disabled={processingWizard || wizardLoading}>
										{processingWizard ? "Processing..." : wizardLoading ? "Loading..." : "Run and Deploy"}
									</Button>
								</div>
							</div>
						</div>
					</div>
				)}
				{/* Configuration Section */}

				{/* Ready section */}
				{isRunning && !showConfigOverride && (
					<div className="row">
						<div className="col-md-12">
							<div className="assistant-config-card">
								<div className="assistant-config-header">
									<h5 className="assistant-config-title">You're all set up!</h5>
								</div>
								<div className="assistant-config-content">
									<div className="text-center py-2">
										<div className="mb-3">
											<i className="bi bi-check-circle-fill text-success" style={{ fontSize: "3rem" }}></i>
										</div>
										<h5 className="mb-2 text-white">Your assistant is running 🎉 </h5>
										<p className="text-muted mb-0">Your agent was triggered and will also run on a schedule. Check runs for output.</p>
									</div>
								</div>
								<div className="assistant-config-footer pt-2">
									<Button
										variant="outline-secondary"
										onClick={() => {
											setShowReconfigureConfirmation(true);
										}}
										className="me-2">
										Reconfigure
									</Button>
									<Button variant="primary" onClick={() => navigate("/manage/runs")}>
										View Runs
									</Button>
								</div>
							</div>
						</div>
					</div>
				)}
				{/* Ready Section */}

				{/* Running Section */}
				{isRunning && (
					<div className="row mt-3">
						<div className="col-md-12">
							<div className="assistant-running-card">
								<div className="d-flex justify-content-between align-items-center">
									<div>
										<h5 className="mb-0 text-white">
											<i className="bi bi-clock-history me-2" style={{ fontSize: "1.3rem", verticalAlign: "middle" }}></i>
											{displayText || "Scheduled..."}
										</h5>
									</div>
									<div>
										<Button
											variant="outline-danger"
											onClick={() => {
												setShowStopConfirmation(true);
											}}>
											Stop
										</Button>
									</div>
								</div>
							</div>
						</div>
					</div>
				)}
				{/* Running Section */}

				{/* Stop Confirmation Modal */}
				<Modal show={showStopConfirmation} onHide={() => setShowStopConfirmation(false)} centered>
					<Modal.Header closeButton>
						<Modal.Title>Confirm Stop</Modal.Title>
					</Modal.Header>
					<Modal.Body>
						<p>Are you sure you want to stop your deployment? You will not receive updates from the assistant.</p>
					</Modal.Body>
					<Modal.Footer>
						<Button variant="secondary" onClick={() => setShowStopConfirmation(false)}>
							Cancel
						</Button>
						<Button variant="danger" onClick={handleStopDeployment}>
							Stop Deployment
						</Button>
					</Modal.Footer>
				</Modal>

				{/* Reconfigure Confirmation Modal */}
				<Modal show={showReconfigureConfirmation} onHide={() => setShowReconfigureConfirmation(false)} centered>
					<Modal.Header closeButton>
						<Modal.Title>Confirm Reconfigure</Modal.Title>
					</Modal.Header>
					<Modal.Body>
						<p>Are you sure you want to reconfigure your assistant? Your current assistant is already running.</p>
					</Modal.Body>
					<Modal.Footer>
						<Button variant="secondary" onClick={() => setShowReconfigureConfirmation(false)}>
							Cancel
						</Button>
						<Button variant="primary" onClick={handleReconfigure}>
							Reconfigure
						</Button>
					</Modal.Footer>
				</Modal>
			</div>
		</div>
	);
};

export default AssistantComponent;
