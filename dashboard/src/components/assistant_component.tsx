import React, { useEffect, useState } from "react";
import { usePostHog } from "posthog-js/react";
import { useToast } from "../utils/toast_context";
import { useRefresh } from "../utils/RefreshContext";
import { Button, Form, Spinner, Modal } from "react-bootstrap";
import { fetchTemplateApi, setDataForKeyApi, runDAGApi, fetchDataForKeyAPI } from "../services/project_services";
import { deployProjectApi } from "../services/navbar_services";
import { fetchRunningDeploymentApi, stopDeploymentApi } from "../services/deployment_services";
import { useNavigate, useSearchParams } from "react-router-dom";
import { fetchAllProjectsAPI } from "../services/all_projects_services";
import { fetchResourcesApi } from "../services/assistant_services";
import InputFactory from "./configuration/InputFactory";
import ResourceSelectionPopup from "./ResourceSelectionPopup";
import "./assistant_component.css";

const OAUTH_INPUTS = ["github"];

const AssistantComponent: React.FC = () => {
	const { showToast } = useToast();
	const { shouldRefresh } = useRefresh();
	const posthog = usePostHog();
	const navigate = useNavigate();
	const [searchParams] = useSearchParams();

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
	const [showIntegrationModal, setShowIntegrationModal] = useState(false);
	const [integrationSuccess, setIntegrationSuccess] = useState(false);
	const [resources, setResources] = useState<any[]>([]);
	const [showResourcePopup, setShowResourcePopup] = useState(false);
	const [currentProviderName, setCurrentProviderName] = useState<string>("");

	const fetch_wizard_inputs = async (template_key: string) => {
		setWizardLoading(true);
		try {
			const template_data = await fetchTemplateApi(template_key);
			const input_array = template_data.input_array;
			setWizardInputs(input_array);

			// Initialize with defaults first
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

			// Fetch existing data for each input key
			await fetchExistingDataForInputs(input_array, defaults);
		} catch (err) {
			console.error("Error fetching assistant:", err);
			showToast("Could not find anything to configure.", "warning");
		} finally {
			setWizardLoading(false);
		}
	};

	const fetchExistingDataForInputs = async (input_array: any[], defaults: Record<string, string>) => {
		const updatedValues = { ...defaults };

		// Fetch data for each input key
		for (const input of input_array) {
			try {
				var fetch_key = input.key;
				if (OAUTH_INPUTS.includes(input.type)) {
					fetch_key = input.key + "_access_token";
				}
				const response = await fetchDataForKeyAPI(fetch_key);
				if (response && response.data !== undefined && response.data !== null) {
					// Convert the data to string if it's not already
					const dataValue = typeof response.data === "string" ? response.data : JSON.stringify(response.data);
					updatedValues[input.key] = dataValue;
				}
			} catch (error) {
				// If there's an error fetching data for this key, keep the default value
				console.log(`No existing data found for key: ${input.key}`);
			}
		}

		// Update the wizard values with fetched data
		setWizardValues(updatedValues);
	};

	const handleUrlParameters = async () => {
		const projectKey = searchParams.get("project_key");
		const integrationComplete = searchParams.get("is_integration_complete");

		if (projectKey) {
			// Store project key and env to localStorage
			localStorage.setItem("selected_project_key", projectKey);
			localStorage.setItem("selected_env_key", projectKey + "_default");

			// Check if we already have the project data in localStorage
			const existingProjectsArray = localStorage.getItem("projects_array");
			const existingSelectedProject = localStorage.getItem("selected_project");

			let needsProjectFetch = false;
			let selectedProject = null;

			if (existingProjectsArray && existingSelectedProject) {
				try {
					selectedProject = JSON.parse(existingSelectedProject);
					if (selectedProject.project_key !== projectKey) {
						needsProjectFetch = true;
					}
				} catch (error) {
					needsProjectFetch = true;
				}
			} else {
				needsProjectFetch = true;
			}

			// Only fetch projects API if we don't have the data or it doesn't match
			if (needsProjectFetch) {
				try {
					const projectsData = await fetchAllProjectsAPI();
					const projectArray = projectsData.project_array;
					selectedProject = projectArray.find((project: any) => project.project_key === projectKey);

					if (selectedProject) {
						// Store project data in localStorage
						localStorage.setItem("selected_project", JSON.stringify(selectedProject));
						localStorage.setItem("projects_array", JSON.stringify(projectArray));
					}
				} catch (error) {
					console.error("Error fetching projects:", error);
					showToast("Error loading project data", "warning");
				}
			}
		}

		if (integrationComplete !== null) {
			const isSuccess = integrationComplete === "1";
			setIntegrationSuccess(isSuccess);
			setShowIntegrationModal(true);
		}
	};

	const refreshData = async () => {
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
		await fetch_wizard_inputs(templateKeyValue);
		await fetchRunning();
	};

	useEffect(() => {
		const initializeComponent = async () => {
			// Handle URL parameters first
			await handleUrlParameters();

			// Refresh data after handling URL parameters
			await refreshData();

			// Pageview context for assistant page
			try {
				posthog?.capture("$pageview", {
					page_category: "assistant",
					project_id: localStorage.getItem("selected_project_key") || undefined,
					environment: localStorage.getItem("selected_env_key") || undefined,
				});
			} catch (_err) {}
		};

		initializeComponent();
	}, [searchParams]);

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
		// Refresh data when shouldRefresh changes (but not on initial load)
		if (shouldRefresh) {
			refreshData();
		}
	}, [shouldRefresh]);

	const handleWizardInputChange = (key: string, value: string) => {
		setWizardValues((prev) => ({ ...prev, [key]: value }));
	};

	const handleSelectResources = async (inputData: any) => {
		try {
			console.log("Select Resources clicked with input data:", inputData);

			// Use the type of the input data as provider_name
			const providerName = inputData.type;

			if (!providerName) {
				showToast("No provider type found in input data", "warning");
				return;
			}

			// Call the fetch resources API
			const response = await fetchResourcesApi(providerName);
			const resources = response.resources;
			setResources(resources);
			setCurrentProviderName(providerName);
			setShowResourcePopup(true);
			console.log("Resources fetched successfully for ", providerName, " : ", resources);
		} catch (error) {
			console.error("Error fetching resources:", error);
			showToast(`Failed to fetch resources: ${error}`, "danger");
		}
	};

	const handleResourceSave = async (selectedResources: any[]) => {
		try {
			console.log("Selected resources:", selectedResources);

			// Create the key based on provider name
			const resourceKey = `${currentProviderName}_selected_resources`;

			// Convert selected resources to JSON string
			const resourcesJson = JSON.stringify(selectedResources);

			// Store using setDataForKeyApi
			await setDataForKeyApi(resourcesJson, resourceKey, "json");

			showToast(`Selected ${selectedResources.length} resource(s) saved successfully`, "success");
		} catch (error) {
			console.error("Error saving selected resources:", error);
			showToast(`Failed to save selected resources: ${error}`, "danger");
		}
	};

	const handleResourcePopupClose = () => {
		setShowResourcePopup(false);
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
				const value = wizardValues[input.key];
				// Determine data type based on value format. ToDo: Temporary hack. May just work.
				const dataType = value && (value.startsWith("[") || value.startsWith("{")) ? "json" : "string";
				await setDataForKeyApi(value, input.key, dataType);
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
															selectResources={handleSelectResources}
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

				{/* Integration Status Modal */}
				<Modal
					show={showIntegrationModal}
					onHide={async () => {
						setShowIntegrationModal(false);
						// Refresh data after dismissing the modal
						await refreshData();
					}}
					centered>
					<Modal.Header closeButton>
						<Modal.Title>
							{integrationSuccess ? (
								<>
									<i className="bi bi-check-circle-fill text-success me-2"></i>
									Successfully Connected
								</>
							) : (
								<>
									<i className="bi bi-exclamation-triangle-fill text-danger me-2"></i>
									Connection Failed
								</>
							)}
						</Modal.Title>
					</Modal.Header>
					<Modal.Body>
						{integrationSuccess ? (
							<p>Your integration has been successfully connected! You can now configure and use your assistant.</p>
						) : (
							<p>There was an error connecting your integration. Please try again or contact support if the issue persists.</p>
						)}
					</Modal.Body>
					<Modal.Footer>
						<Button
							variant="primary"
							onClick={async () => {
								setShowIntegrationModal(false);
								// Refresh data after dismissing the modal
								await refreshData();
							}}>
							{integrationSuccess ? "Continue" : "OK"}
						</Button>
					</Modal.Footer>
				</Modal>

				{/* Resource Selection Popup */}
				<ResourceSelectionPopup
					isOpen={showResourcePopup}
					onClose={handleResourcePopupClose}
					resources={resources}
					onSave={handleResourceSave}
					providerName={currentProviderName}
				/>
			</div>
		</div>
	);
};

export default AssistantComponent;
