import React, { useEffect, useState } from "react";
import { usePostHog } from "posthog-js/react";
import { useToast } from "../utils/toast_context";
import { useRefresh } from "../utils/RefreshContext";
import { Button, Form, Spinner, Modal } from "react-bootstrap";
import { fetchTemplateApi, setDataForKeyApi, runDAGApi, fetchDataForKeyAPI, updateNodeApi, fetchNodesApi } from "../services/project_services";
import { deployProjectApi } from "../services/navbar_services";
import { fetchRunningDeploymentApi, stopDeploymentApi, checkAssistantUpdateApi, upgradeAssistantApi } from "../services/deployment_services";
import { useNavigate, useSearchParams } from "react-router-dom";
import { fetchAllProjectsAPI } from "../services/all_projects_services";
import { fetchResourcesApi } from "../services/assistant_services";
import { BASE_URL } from "../services/base_service";
import { convertToString, determineDataType } from "../utils/shared_functions";
import InputFactory from "./configuration/InputFactory";
import ResourceSelectionPopup from "./ResourceSelectionPopup";
import { PROVIDER_CONFIGS } from "./configuration/providerConfigs";
import "./assistant_component.css";

const OAUTH_INPUTS = ["github", "hubspot", "slack", "linear"];

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
	const [optionalInputs, setOptionalInputs] = useState<any[]>([]);
	const [wizardValues, setWizardValues] = useState<Record<string, string>>({});
	const [wizardSelectedResources, setWizardSelectedResources] = useState<Record<string, any>>({});
	const [processingWizard, setProcessingWizard] = useState(false);
	const [wizardLoading, setWizardLoading] = useState(false);
	const [showOptionalInputs, setShowOptionalInputs] = useState(false);
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
	const [currentInputKey, setCurrentInputKey] = useState<string>("");
	const [currentResourceProperties, setCurrentResourceProperties] = useState<any[]>([]);
	const [showWebhookModal, setShowWebhookModal] = useState(false);
	const [webhookUrl, setWebhookUrl] = useState("");
	const [webhookCopied, setWebhookCopied] = useState(false);
	const [successMessage, setSuccessMessage] = useState("Your agent was triggered and will also run on a schedule.");
	const [templateData, setTemplateData] = useState<any | null>(null);
	const [highlightResourceKeys, setHighlightResourceKeys] = useState<string[]>([]);
	const [runOnceStarted, setRunOnceStarted] = useState(false);
	const [updateAvailable, setUpdateAvailable] = useState(false);
	const [, setUpdateCommitMessage] = useState("");
	const [upgrading, setUpgrading] = useState(false);
	const fetch_wizard_inputs = async (template_key: string) => {
		setWizardLoading(true);
		try {
			const template_data = await fetchTemplateApi(template_key);
			const input_array = template_data.input_array;
			const optional_input_array = template_data.optional_input_array || [];
			setTemplateData(template_data);
			const success_message = template_data.success_message;
			setSuccessMessage(success_message);
			setWizardInputs(input_array);
			setOptionalInputs(optional_input_array);

			// Combine both arrays for initialization
			const allInputs = [...input_array, ...optional_input_array];

			// Initialize with defaults first
			const defaults: Record<string, string> = {};
			allInputs.forEach((i: any) => {
				if (i.value !== undefined) {
					defaults[i.key] = i.value;
				} else if (Array.isArray(i.options) && i.options.length > 0) {
					// Extract the key/value from the first option object
					const firstOption = i.options[0];
					defaults[i.key] = typeof firstOption === "string" ? firstOption : firstOption.key;
				} else {
					defaults[i.key] = "";
				}
			});
			setWizardValues(defaults);

			// Fetch existing data for each input key
			await fetchExistingDataForInputs(allInputs, defaults);
		} catch (err) {
			console.error("Error fetching assistant:", err);
			showToast("Could not find anything to configure.", "warning");
		} finally {
			setWizardLoading(false);
		}
	};

	const fetchExistingDataForInputs = async (input_array: any[], defaults: Record<string, string>) => {
		const updatedValues = { ...defaults };
		const updatedSelectedResources: Record<string, any> = {};

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

			// For OAuth inputs, also fetch selected resources
			if (OAUTH_INPUTS.includes(input.type)) {
				try {
					const resources_key = input.key + "_selected_resources";
					const resourcesResponse = await fetchDataForKeyAPI(resources_key);
					if (resourcesResponse && resourcesResponse.data !== undefined && resourcesResponse.data !== null) {
						// Parse the JSON string to get the actual resources array
						const resourcesData = typeof resourcesResponse.data === "string" ? JSON.parse(resourcesResponse.data) : resourcesResponse.data;
						updatedSelectedResources[input.key] = resourcesData;
					}
				} catch (error) {
					// If there's an error fetching selected resources, just log it
					console.log(`No existing selected resources found for key: ${input.key}`);
				}
			}
		}

		// Update the wizard values and selected resources with fetched data
		setWizardValues(updatedValues);
		setWizardSelectedResources(updatedSelectedResources);
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
		let templateKeyValue = projectData.template_key || projectData.project_key || localStorage.getItem("template_key") || "";

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
		await checkForUpdate();
	};

	const checkForUpdate = async () => {
		try {
			const data = await checkAssistantUpdateApi();
			if (data.has_update) {
				setUpdateAvailable(true);
				setUpdateCommitMessage(data.latest_commit_message || "");
			} else {
				setUpdateAvailable(false);
			}
		} catch {
			// Silently ignore — non-assistant projects or network issues
		}
	};

	const handleUpgrade = async () => {
		setUpgrading(true);
		try {
			await upgradeAssistantApi();

			setUpdateAvailable(false);
			showToast("Assistant upgraded successfully.", "success");
			await refreshData();
		} catch (error) {
			console.error("Upgrade failed:", error);
			showToast("Upgrade failed: " + error, "danger");
		} finally {
			setUpgrading(false);
		}
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
			setCurrentInputKey(inputData.key);
			setCurrentResourceProperties(inputData.resource_properties || []);
			setShowResourcePopup(true);
			console.log("Resources fetched successfully for ", providerName, " : ", resources);
		} catch (error) {
			console.error("Error fetching resources:", error);

			// Parse error message and provide user-friendly feedback
			let errorMessage = "Failed to fetch resources. Please try again.";
			const errorStr = error instanceof Error ? error.message : String(error);

			if (errorStr.includes("401") || errorStr.toLowerCase().includes("unauthorized")) {
				errorMessage = "Authentication failed. Your token has expired or is invalid. Please reconnect or update your access token.";
			} else if (errorStr.includes("403") || errorStr.toLowerCase().includes("forbidden")) {
				errorMessage = "Access denied. Please ensure your token has the required permissions to access repositories.";
			} else if (errorStr.includes("404") || errorStr.toLowerCase().includes("not found")) {
				errorMessage = "Resources not found. Please verify your connection and try again.";
			} else if (errorStr.toLowerCase().includes("network") || errorStr.toLowerCase().includes("timeout")) {
				errorMessage = "Network error. Please check your internet connection and try again.";
			} else if (errorStr.includes("Missing user ID") || errorStr.includes("project key")) {
				errorMessage = "Session error. Please refresh the page and try again.";
			} else if (errorStr && errorStr.length < 100) {
				// If it's a short, specific error message from backend, show it
				errorMessage = errorStr;
			}

			showToast(errorMessage, "danger");
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

			// Update the local state immediately
			setWizardSelectedResources((prev) => ({
				...prev,
				[currentInputKey]: selectedResources,
			}));

			showToast(`Selected ${selectedResources.length} resource(s) saved successfully`, "success");
		} catch (error) {
			console.error("Error saving selected resources:", error);
			showToast(`Failed to save selected resources: ${error}`, "danger");
		}
	};

	const handleResourcePopupClose = () => {
		setShowResourcePopup(false);
	};

	const hasEmptyInputs = () => {
		return wizardInputs.some((input) => {
			const value = wizardValues[input.key];

			// Check if value is empty, null, undefined
			if (!value) {
				return true;
			}

			// Convert to string first to ensure consistent handling
			const stringValue = convertToString(value);

			// Check if string value is empty or just whitespace
			if (!stringValue || stringValue.trim() === "") {
				return true;
			}

			// Try to parse as JSON - if it's a JSON array, check if it's empty
			try {
				const parsed = JSON.parse(stringValue);
				if (Array.isArray(parsed) && parsed.length === 0) {
					return true;
				}
			} catch {
				// Not valid JSON, treat as regular string - already handled above
			}

			// For OAuth inputs that require resource selection, also check if at least 1 resource is selected
			if (OAUTH_INPUTS.includes(input.type) && PROVIDER_CONFIGS[input.type]?.hasSelectResources) {
				const selectedResources = wizardSelectedResources[input.key];
				if (!selectedResources || !Array.isArray(selectedResources) || selectedResources.length === 0) {
					return true;
				}
			}

			return false;
		});
	};

	const handleScheduleInput = async (value: string, key: string) => {
		console.log("=== Schedule Input Handler ===");
		console.log("Schedule Key:", key);
		console.log("Schedule Value:", value);

		try {
			//convert to string if not
			value = convertToString(value);
			const parsed = JSON.parse(value);
			console.log("Parsed Schedule Data:", parsed);

			// Convert new format to old format that backend expects
			let scheduleData: any = {};

			if (parsed.interval) {
				console.log(`Interval Schedule: Every ${parsed.interval.every} ${parsed.interval.period}`);
				scheduleData = {
					schedule_type: "interval",
					interval_every: String(parsed.interval.every),
					interval_type: parsed.interval.period,
				};
			} else if (parsed.cron) {
				console.log(`Cron Schedule: ${parsed.cron} (${parsed.timezone})`);
				const cronParts = parsed.cron.split(" ");
				if (cronParts.length === 5) {
					scheduleData = {
						schedule_type: "crontab",
						crontab_minutes: cronParts[0],
						crontab_hours: cronParts[1],
						crontab_days_of_month: cronParts[2],
						crontab_months_of_year: cronParts[3],
						crontab_days_of_week: cronParts[4],
						crontab_timezone: parsed.timezone || "UTC",
					};
				} else {
					console.error("Invalid cron expression format");
					throw new Error("Invalid cron expression format");
				}
			} else if (parsed.manual) {
				console.log("Manual/Webhook Only Schedule");
				scheduleData = {
					schedule_type: "none",
				};
			} else {
				// Already in old format, use as-is
				scheduleData = parsed;
			}

			console.log("Converted Schedule Data:", scheduleData);

			// Fetch the starting node to get its current data
			const nodesData = await fetchNodesApi();
			const startingNode = nodesData.node_array.find((n: any) => n.is_starting_node);

			if (!startingNode) {
				throw new Error("No starting node found");
			}

			console.log("Starting Node:", startingNode.node_key);

			// Build the update data by merging current node data with schedule changes
			const updateData = {
				name: startingNode.name,
				is_enabled: true,
				is_starting_node: true,
				...scheduleData,
				input_data_key_array: startingNode.input_data_key_array || [],
				output_data_key_array: startingNode.output_data_key_array || [],
				run_after_nodes_array: startingNode.run_after_nodes_array || [],
			};

			console.log("Update Data:", updateData);

			// Call updateNodeApi like nodes component does
			await updateNodeApi(startingNode.node_key, updateData);
			console.log("Node schedule updated successfully");
		} catch (error) {
			console.error("Error handling schedule data:", error);
			throw error;
		}

		console.log("=============================");
	};

	const handleRunAndDeploy = async (shouldDeploy: boolean = true) => {
		// Validate that all required inputs have values
		const emptyInputs = wizardInputs.filter((input) => {
			const value = wizardValues[input.key];
			console.log("value", value);
			console.log("input", input);
			console.log("wizardValues", wizardValues);

			// Check if value is empty, null, undefined
			if (!value) {
				return true;
			}

			// Convert to string first to ensure consistent handling
			const stringValue = convertToString(value);

			// Check if string value is empty or just whitespace
			if (!stringValue || stringValue.trim() === "") {
				return true;
			}

			// Try to parse as JSON - if it's a JSON array, check if it's empty
			try {
				const parsed = JSON.parse(stringValue);
				if (Array.isArray(parsed) && parsed.length === 0) {
					return true;
				}
			} catch {
				// Not valid JSON, treat as regular string - already handled above
			}

			return false;
		});

		if (emptyInputs.length > 0) {
			showToast("Please provide all required fields and connections", "warning");
			return;
		}

		// Validate that OAuth inputs that require resource selection have at least 1 resource selected
		const oauthInputsWithoutResources = wizardInputs.filter((input) => {
			if (OAUTH_INPUTS.includes(input.type) && PROVIDER_CONFIGS[input.type]?.hasSelectResources) {
				const selectedResources = wizardSelectedResources[input.key];
				return !selectedResources || !Array.isArray(selectedResources) || selectedResources.length === 0;
			}
			return false;
		});

		if (oauthInputsWithoutResources.length > 0) {
			showToast("Please select at least 1 resource for all integrations", "warning");
			const keysToHighlight = oauthInputsWithoutResources.map((i) => i.key);
			setHighlightResourceKeys(keysToHighlight);
			setTimeout(() => setHighlightResourceKeys([]), 4000);
			return;
		}

		setProcessingWizard(true);
		try {
			// Merge both required and optional inputs
			const allInputs = [...wizardInputs, ...optionalInputs];

			// Save all inputs
			for (const input of allInputs) {
				const value = wizardValues[input.key];
				if (value) {
					// Check if this is a schedule type input
					if (input.type === "schedule") {
						await handleScheduleInput(value, input.key);
					} else {
						// Convert value to string and determine data type
						const stringValue = convertToString(value);
						const dataType = determineDataType(value);
						await setDataForKeyApi(stringValue, input.key, dataType);
					}
				}
			}

			const env = localStorage.getItem("selected_env_key") || "";
			console.log("Running DAG with starting node key: ", startingNodeKey, "and env: ", env);
			await runDAGApi(null, env);

			if (shouldDeploy) {
				var version_code_string = `0.${Math.floor(Math.random() * 101)}.${Math.floor(Math.random() * 101)}`;
				console.log("Deploying project with version code: ", version_code_string);
				await deployProjectApi(version_code_string);

				// Push event to Google Tag Manager
				const projectKey = localStorage.getItem("selected_project_key");
				const projectData = JSON.parse(localStorage.getItem("selected_project") || "{}");
				// Curated assistants log their template_key directly (e.g. "gitzoid").
				// WaveMaker-built projects log under a wavemaker: namespace so analytics
				// dashboards can distinguish the two cohorts cleanly.
				const assistantKey = projectData.template_key
					|| (projectData.project_key ? `wavemaker:${projectData.project_key}` : "unknown_assistant");
				const uid = localStorage.getItem("uid");

				// Track deployment success
				if (window?.dataLayer) {
					window.dataLayer.push({
						event: "assistant_deployed",
						user_id: uid,
						project_id: projectKey,
						assistant_key: assistantKey,
						value: 10,
						deployment_status: "success",
					});
				}

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
			} else {
				// For run once, show temporary success view
				setRunOnceStarted(true);
				showToast("Run started successfully", "success");
			}
		} catch (error) {
			console.error("Wizard run failed:", error);
			showToast("" + error, "danger");
		} finally {
			setProcessingWizard(false);
		}
	};

	const handleRunOnce = async () => {
		await handleRunAndDeploy(false);
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

	// Show webhook section when GitHub is configured and display_type is not "no-webhook" (e.g. "base" or undefined)
	const shouldShowGitHubWebhook = () => {
		const githubInput = wizardInputs.find((input) => input.type === "github");
		if (!githubInput) return false;
		return githubInput.display_type !== "no-webhook";
	};

	// Generate webhook URL
	const generateWebhookUrl = (): string => {
		const baseUrl = `${BASE_URL}/webhook/run`;
		const uid = localStorage.getItem("uid");
		const projectKey = localStorage.getItem("selected_project_key");
		const envKey = projectKey + "_default";

		// Get the first node key from running deployment if available
		const nodeKey = "fetch_pull_requests";

		if (!uid || !projectKey || !envKey || !nodeKey) {
			return ""; // Cannot generate webhook if any piece is missing
		}
		return `${baseUrl}/${uid}/${projectKey}/${nodeKey}/${envKey}/`;
	};

	const handleViewWebhook = () => {
		const url = generateWebhookUrl();
		setWebhookUrl(url);
		setShowWebhookModal(true);
		setWebhookCopied(false);
	};

	const handleCopyWebhook = () => {
		navigator.clipboard.writeText(webhookUrl);
		setWebhookCopied(true);
		setTimeout(() => setWebhookCopied(false), 2000);
	};

	return (
		<div className="main-container assistant-container">
			<div className="mt-3 d-flex flex-column" style={{ height: "100%" }}>
				{/* Header */}
				<div className="assistant-header">
					<h3 className="assistant-title">Welcome, {userName}!</h3>
				</div>

				{/* Update Available Banner */}
				{updateAvailable && (
					<div className="row mb-3">
						<div className="col-md-12">
							<div className="assistant-update-banner">
								<div className="d-flex align-items-center justify-content-between">
									<div className="d-flex align-items-center">
										<i className="bi bi-arrow-up-circle-fill me-3" style={{ fontSize: "1.5rem", color: "#1ED66C" }}></i>
										<div>
											<h6 className="mb-0 text-white">New version available</h6>
											<p className="mb-0 text-muted" style={{ fontSize: "0.85rem" }}>
												Upgrade your assistant to get the latest improvements.
											</p>
										</div>
									</div>
									<Button variant="outline-success" size="sm" onClick={handleUpgrade} disabled={upgrading} style={{ minWidth: "100px" }}>
										{upgrading ? (
											<>
												<Spinner animation="border" size="sm" className="me-1" />
												Upgrading...
											</>
										) : (
											<>
												{/* <i className="bi bi-arrow-up me-1"></i> */}
												Upgrade
											</>
										)}
									</Button>
								</div>
							</div>
						</div>
					</div>
				)}

				{/* Configuration Section */}
				{(!isRunning || showConfigOverride) && !runOnceStarted && (
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
											{wizardInputs.length === 0 && optionalInputs.length === 0 ? (
												<div className="text-center py-4">
													<div className="mb-3">
														<i className="bi bi-check-circle-fill text-success" style={{ fontSize: "3rem" }}></i>
													</div>
													<h5 className="mb-3 text-white">Ready to run!</h5>
													<p className="text-white mb-0">Your agent is ready to go. No additional configuration is needed.</p>
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
															selectedResources={wizardSelectedResources[input_dict.key]}
															onRefresh={refreshData}
															highlightSelectResources={highlightResourceKeys.includes(input_dict.key)}
														/>
													))}

													{/* Optional Inputs Section */}
													{optionalInputs.length > 0 && (
														<div className="mt-4">
															<Button
																variant="outline-secondary"
																size="sm"
																className="mb-3"
																onClick={() => setShowOptionalInputs(!showOptionalInputs)}
																aria-expanded={showOptionalInputs}>
																<i className={`bi bi-chevron-${showOptionalInputs ? "up" : "down"} me-2`}></i>
																Other Options ({optionalInputs.length})
															</Button>

															{showOptionalInputs && (
																<div className="optional-inputs-section">
																	{optionalInputs.map((input_dict) => (
																		<InputFactory
																			key={input_dict.key}
																			inputConfig={input_dict}
																			value={wizardValues[input_dict.key] || ""}
																			onChange={(value) => handleWizardInputChange(input_dict.key, value)}
																			selectResources={handleSelectResources}
																			selectedResources={wizardSelectedResources[input_dict.key]}
																			onRefresh={refreshData}
																			isOptional={true}
																			highlightSelectResources={highlightResourceKeys.includes(input_dict.key)}
																		/>
																	))}
																</div>
															)}
														</div>
													)}
												</Form>
											)}
											{templateData?.configuration_helper_message && (
												<div className="alert bg-transparent text-white mb-4" style={{ fontSize: "0.8rem", border: "1px solid #2D313A" }}>
													<i className="bi bi-info-circle me-2 text-secondary-wa"></i>
													{templateData.configuration_helper_message}
												</div>
											)}
										</>
									)}
								</div>

								<div className="assistant-config-footer d-flex gap-2">
									<Button
										variant="secondary"
										className={`assistant-action-button assistant-run-once-button ${hasEmptyInputs() ? "opacity-50" : ""}`}
										onClick={handleRunOnce}
										disabled={processingWizard || wizardLoading}
										style={hasEmptyInputs() ? { cursor: "not-allowed" } : {}}>
										{processingWizard ? (
											"Processing..."
										) : wizardLoading ? (
											"Loading..."
										) : (
											<>
												<i className="bi bi-play-fill" aria-hidden="true"></i>
												<span>Run Once</span>
											</>
										)}
									</Button>
									<Button
										className={`assistant-action-button assistant-deploy-button ${hasEmptyInputs() ? "opacity-50" : ""}`}
										onClick={() => handleRunAndDeploy(true)}
										disabled={processingWizard || wizardLoading}
										style={hasEmptyInputs() ? { cursor: "not-allowed" } : {}}>
										{processingWizard ? (
											"Processing..."
										) : wizardLoading ? (
											"Loading..."
										) : (
											<>
												<i className="bi bi-lightning-charge-fill" aria-hidden="true"></i>
												<span>Enable Assistant</span>
											</>
										)}
									</Button>
								</div>
							</div>
						</div>
					</div>
				)}
				{/* Configuration Section */}

				{/* Run Once Success Section */}
				{runOnceStarted && (
					<div className="row">
						<div className="col-md-12">
							<div className="assistant-config-card">
								<div className="assistant-config-header">
									<h5 className="assistant-config-title">Run Started!</h5>
								</div>
								<div className="assistant-config-content">
									<div className="text-center py-2">
										<div className="mb-3">
											<i className="bi bi-check-circle-fill text-success" style={{ fontSize: "3rem" }}></i>
										</div>
										<h5 className="mb-2 text-white">Run started successfully.</h5>
										<p className="text-muted mb-0">Your one-time run is in progress. Open output to track results.</p>
									</div>
								</div>
								<div className="assistant-config-footer pt-2">
									<Button
										variant="outline-secondary"
										onClick={() => {
											setRunOnceStarted(false);
										}}
										className="me-2">
										Back to Config
									</Button>
									<Button variant="primary" onClick={() => navigate("/manage/runs")}>
										View Output
									</Button>
								</div>
							</div>
						</div>
					</div>
				)}
				{/* Run Once Success Section */}

				{/* Ready section */}
				{isRunning && !showConfigOverride && !runOnceStarted && (
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
										<h5 className="mb-2 text-white">Assistant is running successfully.</h5>
										<p className="text-muted mb-0">{successMessage}</p>
										<p className="text-muted mb-0">Open output to view activity and results.</p>
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
										View Output
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

				{/* GitHub Webhook Helper Section - shown when GitHub is configured and display_type is not "no-webhook" */}
				{isRunning && shouldShowGitHubWebhook() && (
					<div className="row mt-3">
						<div className="col-md-12">
							<div className="assistant-config-card" style={{ borderLeft: "3px solid #1ED66C" }}>
								<div className="assistant-config-content">
									<div className="d-flex align-items-start">
										<div className="me-3">
											<i className="bi bi-github" style={{ fontSize: "2rem", color: "#1ED66C" }}></i>
										</div>
										<div className="flex-grow-1">
											<h6 className="text-white mb-2">Enable Real-time GitHub Connect (Optional)</h6>
											<p className="text-muted mb-2" style={{ fontSize: "0.9rem" }}>
												Configure a webhook in your github repository to have the agent run in realtime.
											</p>
											<Button variant="outline-success" size="sm" onClick={handleViewWebhook}>
												<i className="bi bi-link-45deg me-1"></i>
												View Webhook
											</Button>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				)}

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
							<p className="text-white my-4 mx-4">Your integration has been successfully connected! You can now configure and use your assistant.</p>
						) : (
							<p className="text-white my-4 mx-4">
								There was an error connecting your integration. Please try again or contact support if the issue persists.
							</p>
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
					initiallySelectedResources={wizardSelectedResources[currentInputKey] || []}
					resourceProperties={currentResourceProperties}
				/>

				{/* Webhook Modal */}
				<Modal show={showWebhookModal} onHide={() => setShowWebhookModal(false)} centered size="lg">
					<Modal.Header closeButton>
						<Modal.Title>GitHub Webhook Configuration</Modal.Title>
					</Modal.Header>
					<Modal.Body>
						<div>
							<div>
								<label className="form-label text-white" style={{ fontSize: "0.9rem" }}>
									Webhook URL
								</label>
								<div className="input-group">
									<input
										type="text"
										className="form-control text-white"
										value={webhookUrl}
										readOnly
										disabled
										style={{ fontFamily: "monospace", fontSize: "0.9rem", backgroundColor: "#1C1F28", border: "1px solid #2D313A" }}
									/>
									<Button variant="outline-success" onClick={handleCopyWebhook}>
										{webhookCopied ? (
											<>
												<i className="bi bi-check-lg me-1"></i>
												Copied!
											</>
										) : (
											<>
												<i className="bi bi-clipboard me-1"></i>
												Copy
											</>
										)}
									</Button>
								</div>
							</div>
							<p className="text-secondary-wa my-3">Use this webhook URL to run the agent in realtime.</p>

							<div className="mt-3">
								<a
									href="https://waveassist.ai/blog/how-to-set-up-github-webhook-for-waveassist"
									target="_blank"
									rel="noopener noreferrer"
									className="text-success text-decoration-none">
									<i className="bi bi-question-circle me-1"></i>
									How to configure webhook?
								</a>
							</div>
						</div>
					</Modal.Body>
					<Modal.Footer>
						<Button variant="secondary" onClick={() => setShowWebhookModal(false)}>
							Close
						</Button>
					</Modal.Footer>
				</Modal>
			</div>
		</div>
	);
};

export default AssistantComponent;
