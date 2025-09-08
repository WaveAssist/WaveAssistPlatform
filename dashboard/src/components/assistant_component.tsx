import React, { useEffect, useState, useRef } from "react";
import { usePostHog } from "posthog-js/react";
import { useToast } from "../utils/toast_context";
import { Button, Form, Spinner } from "react-bootstrap";
import { fetchTemplateApi, setDataForKeyApi, runDAGApi } from "../services/project_services";
import { deployProjectApi } from "../services/navbar_services";
import { useNavigate } from "react-router-dom";
import "./assistant_component.css";

const AssistantComponent: React.FC = () => {
	const { showToast } = useToast();
	const posthog = usePostHog();
	const navigate = useNavigate();

	// Get user name from localStorage
	const userData = JSON.parse(localStorage.getItem("user_data") || "{}");
	const userName = userData.name || "User";

	// Wizard state
	const [wizardInputs, setWizardInputs] = useState<any[]>([]);
	const [wizardValues, setWizardValues] = useState<Record<string, string>>({});
	const [processingWizard, setProcessingWizard] = useState(false);
	const [wizardDone, setWizardDone] = useState(false);
	const [wizardLoading, setWizardLoading] = useState(false);
	const [startingNodeKey] = useState<string | null>(null);
	const [templateKey, setTemplateKey] = useState<string>("");

	// Stock search state
	const [stockSearchQuery, setStockSearchQuery] = useState("");
	const [stockSearchResults, setStockSearchResults] = useState<any[]>([]);
	const [stockSearchLoading, setStockSearchLoading] = useState(false);
	const [selectedStocks, setSelectedStocks] = useState<any[]>([]);
	const [stockSearchTimeout, setStockSearchTimeout] = useState<NodeJS.Timeout | null>(null);
	const stockSearchAbortController = useRef<AbortController | null>(null);

	// Maximum allowed stocks constant
	const MAX_SELECTED_STOCKS = 5;

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

	// Cleanup stock search timeout on unmount
	useEffect(() => {
		return () => {
			if (stockSearchTimeout) {
				clearTimeout(stockSearchTimeout);
			}
		};
	}, [stockSearchTimeout]);

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
		setTemplateKey(templateKeyValue);
		fetch_wizard_inputs(templateKeyValue);
	}, []);

	const handleWizardInputChange = (key: string, value: string) => {
		setWizardValues((prev) => ({ ...prev, [key]: value }));
	};

	// Function to format template key for display
	const getTemplateDisplayName = (key: string) => {
		if (!key) return "Setup Assistant";
		return `Setup Assistant`;
	};

	// Stock search functions
	const searchStocks = async (query: string) => {
		if (!query.trim()) {
			setStockSearchResults([]);
			return;
		}

		// Cancel previous request if it exists
		if (stockSearchAbortController.current) {
			stockSearchAbortController.current.abort();
		}

		// Create new abort controller for this request
		stockSearchAbortController.current = new AbortController();

		setStockSearchLoading(true);
		try {
			const response = await fetch(`https://appsapi.waveassist.io/generic/search_stocks/${encodeURIComponent(query)}`, {
				signal: stockSearchAbortController.current.signal,
			});
			const data = await response.json();

			if (data.status === "success" && data.data.stocks) {
				setStockSearchResults(data.data.stocks);
			} else {
				setStockSearchResults([]);
			}
		} catch (error: any) {
			// Don't log error if it was aborted
			if (error.name !== "AbortError") {
				console.error("Stock search failed:", error);
				setStockSearchResults([]);
			}
		} finally {
			setStockSearchLoading(false);
		}
	};

	const handleStockSearchChange = (query: string) => {
		setStockSearchQuery(query);

		// Clear existing timeout
		if (stockSearchTimeout) {
			clearTimeout(stockSearchTimeout);
		}

		// Set new timeout for debounced search
		const timeout = setTimeout(() => {
			searchStocks(query);
		}, 350); // 0.35 seconds delay

		setStockSearchTimeout(timeout);
	};

	const handleStockSelect = (stock: any, key: string) => {
		// Check if stock is already selected
		const isAlreadySelected = selectedStocks.some((s) => s._id === stock._id);
		if (!isAlreadySelected) {
			// Check if we already have maximum stocks selected
			if (selectedStocks.length >= MAX_SELECTED_STOCKS) {
				showToast(`Maximum ${MAX_SELECTED_STOCKS} stocks allowed`, "warning");
				return;
			}

			const newSelectedStocks = [...selectedStocks, stock];
			setSelectedStocks(newSelectedStocks);
			// Update wizard values with selected stocks as CSV
			const stockSymbols = newSelectedStocks.map((s) => s.symbol).join(",");
			setWizardValues((prev) => ({ ...prev, [key]: stockSymbols }));
			// Call handleWizardInputChange with CSV format
			handleWizardInputChange(key, stockSymbols);
		}
		setStockSearchQuery("");
		setStockSearchResults([]);
	};

	const handleStockRemove = (stockId: string, key: string) => {
		const remainingStocks = selectedStocks.filter((s) => s._id !== stockId);
		setSelectedStocks(remainingStocks);
		// Update wizard values with remaining stocks as CSV
		const stockSymbols = remainingStocks.map((s) => s.symbol).join(",");
		setWizardValues((prev) => ({ ...prev, [key]: stockSymbols }));
		// Call handleWizardInputChange with CSV format
		handleWizardInputChange(key, stockSymbols);
	};

	const handleRunAndDeploy = async () => {
		// Validate that all required inputs have values
		const emptyInputs = wizardInputs.filter((input) => {
			const value = wizardValues[input.key];
			// Check if value is empty, null, undefined, or just whitespace
			return !value || value.trim() === "";
		});

		// Additional validation for stock-type inputs
		const stockInputs = wizardInputs.filter((input) => input.type === "stock");
		const hasStockInputs = stockInputs.length > 0;
		const hasNoStocksSelected = selectedStocks.length === 0;

		if (emptyInputs.length > 0) {
			showToast("Please provide input values for all required fields", "warning");
			return;
		}

		if (hasStockInputs && hasNoStocksSelected) {
			showToast("Please select at least one stock from the dropdown", "warning");
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
			setWizardDone(true);
		} catch (error) {
			console.error("Wizard run failed:", error);
			showToast("" + error, "danger");
		} finally {
			setProcessingWizard(false);
		}
	};

	return (
		<div className="main-container assistant-container">
			<div className="mt-3 d-flex flex-column" style={{ height: "100%" }}>
				{/* Header */}
				<div className="assistant-header">
					<h3 className="assistant-title">Welcome, {userName}!</h3>
				</div>

				{/* Two Cards Layout - Similar to Credits */}
				<div className="row">
					{/* Configuration Card */}
					<div className="col-md-12">
						<div className="assistant-config-card">
							<div className="assistant-config-header">
								<h5 className="assistant-config-title">{getTemplateDisplayName(templateKey)}</h5>
							</div>

							<div className="assistant-config-content">
								{wizardDone ? (
									<div className="text-center">
										<h5 className="mb-3">🎉 Your assistant has been successfully deployed! 🎉</h5>
										<p className="text-muted mb-2">You will receive an email notification in the next few minutes.</p>
										<p className="text-muted mb-0">
											Your assistant will continue to run on its scheduled intervals automatically. No further action is required from you.
										</p>
									</div>
								) : wizardLoading ? (
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
													<Form.Group className="mb-3" key={input_dict.key}>
														<Form.Label>{input_dict.key}</Form.Label>
														{input_dict.type === "stock" ? (
															<div>
																{/* Stock Search Input */}
																<Form.Control
																	type="text"
																	placeholder="Search for stocks..."
																	value={stockSearchQuery}
																	onChange={(e) => handleStockSearchChange(e.target.value)}
																/>

																{/* Stock Search Results */}
																{stockSearchLoading && (
																	<div className="mt-2">
																		<Spinner animation="border" size="sm" /> <span className="text-muted">Loading...</span>
																	</div>
																)}

																{stockSearchResults.length > 0 && (
																	<div className="mt-2 stock-search-results-container p-2">
																		{stockSearchResults.map((stock) => (
																			<div
																				key={stock._id}
																				className="p-2 border-bottom stock-search-result"
																				onClick={() => handleStockSelect(stock, input_dict.key)}>
																				<div className="fw-bold">{stock.symbol}</div>
																				<div className="text-muted small">{stock.name}</div>
																				<div className="text-muted small">
																					{stock.exchange} • {stock.country} • {stock.currency}
																				</div>
																			</div>
																		))}
																	</div>
																)}

																{/* Selected Stocks */}
																<div className="mt-3">
																	<small className="text-muted">
																		Selected Stocks ({selectedStocks.length}/{MAX_SELECTED_STOCKS}):
																	</small>
																	{selectedStocks.length > 0 && (
																		<div className="mt-2">
																			{selectedStocks.map((stock) => (
																				<span key={stock._id} className="badge stock-selected-badge">
																					{stock.symbol} - {stock.name}
																					<button
																						type="button"
																						className="btn-close btn-close-white"
																						onClick={() => handleStockRemove(stock._id, input_dict.key)}>
																						X
																					</button>
																				</span>
																			))}
																		</div>
																	)}
																</div>
															</div>
														) : Array.isArray(input_dict.options) && input_dict.options.length > 0 ? (
															<Form.Select
																value={wizardValues[input_dict.key] || input_dict.options[0]}
																onChange={(e) => handleWizardInputChange(input_dict.key, e.target.value)}>
																{input_dict.options.map((opt: string, idx: number) => (
																	<option key={idx} value={opt}>
																		{opt}
																	</option>
																))}
															</Form.Select>
														) : (
															<Form.Control
																type="text"
																value={wizardValues[input_dict.key] || ""}
																onChange={(e) => handleWizardInputChange(input_dict.key, e.target.value)}
															/>
														)}
														{input_dict.helper_message && <Form.Text className="text-secondary">{input_dict.helper_message}</Form.Text>}
													</Form.Group>
												))}
											</Form>
										)}
									</>
								)}
							</div>

							<div className="assistant-config-footer">
								{wizardDone ? (
									<>
										<Button variant="outline-secondary" onClick={() => setWizardDone(false)} className="me-2">
											Configure Again
										</Button>
										<Button variant="outline-success" onClick={() => navigate("/manage/runs")}>
											View Runs
										</Button>
									</>
								) : (
									<Button className="assistant-deploy-button" onClick={handleRunAndDeploy} disabled={processingWizard || wizardLoading}>
										{processingWizard ? "Processing..." : wizardLoading ? "Loading..." : "Run and Deploy"}
									</Button>
								)}
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
};

export default AssistantComponent;
