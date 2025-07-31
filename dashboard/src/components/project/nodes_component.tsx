import React, { useEffect, useState, Suspense } from "react";
import Joyride, { Step } from "react-joyride";
import { Node as RFNode, Edge as RFEdge } from "reactflow";
import {
	fetchNodesApi,
	updateCodeApi,
	createNodeApi,
	updateNodeApi,
	deleteNodeApi,
	runDAGApi,
	setDataForKeyApi,
} from "../../services/project_services";
import { deployProjectApi } from "../../services/navbar_services";
import { useNavigate } from "react-router-dom";
import { useToast } from "../../utils/toast_context";
import { Button, Form, DropdownButton, Dropdown, Spinner } from "react-bootstrap";
import "./project_components.css";
import type { GridOptions } from "ag-grid-community";
import "../../utils/ag-theme-project.css";
import Modal from "react-bootstrap/Modal";
import Editor from "@monaco-editor/react";
import { useForm, Controller } from "react-hook-form";
import timezones from "../../utils/timezones.json";
import { NodeType } from "../../utils/types";
import { useRefresh } from "../../utils/RefreshContext";
import JSZip from "jszip";
import { saveAs } from "file-saver";
import { Badge, Collapse } from "react-bootstrap";
import NodeTableView from "./node_table_view";
import NodeFlowView from "./node_flow_view";
import dagre from "dagre";
import { Position } from "reactflow";
import { applyNodeChanges, NodeChange } from "reactflow";

// Constants for node size
const NODE_WIDTH = 250;
const NODE_HEIGHT = 50;

const NodesComponent: React.FC = () => {
	const { shouldRefresh } = useRefresh();
	// const [isOpen, setIsOpen] = useState(false);
	// const [url, setUrl] = useState("");
	const [showWebhook, setShowWebhook] = useState(false);
	const [showEmailWebhook, setShowEmailWebhook] = useState(false);
	const [webhookUrl, setWebhookUrl] = useState("");
	const [copied, setCopied] = useState(false);
	const [runTour, setRunTour] = useState(false);
	const [emailWebhook, setEmailWebhook] = useState("");
	const [view, setView] = useState<"flow" | "table">(() => {
		const saved = localStorage.getItem("nodesView");
		if (saved === "flow" || saved === "table") return saved;
		return "table";
	});
	const [rfNodes, setRfNodes] = useState<RFNode[]>([]);
	const [rfEdges, setRfEdges] = useState<RFEdge[]>([]);

	// Mobile detection
	const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
	useEffect(() => {
		const handleResize = () => setIsMobile(window.innerWidth < 768);
		window.addEventListener("resize", handleResize);
		return () => window.removeEventListener("resize", handleResize);
	}, []);

	const [showWizard, setShowWizard] = useState(false);
	const [wizardInputs, setWizardInputs] = useState<any[]>([]);
	const [wizardValues, setWizardValues] = useState<Record<string, string>>({});
	const [processingWizard, setProcessingWizard] = useState(false);
	const [wizardDone, setWizardDone] = useState(false);
	const [startingNodeKey, setStartingNodeKey] = useState<string | null>(null);
	const navigate = useNavigate();
	const steps: Step[] = [
		{
			target: ".play-button-step", // The plus icon button
			content: "Click on the play button to run your workflow",
			disableBeacon: true,
			locale: { last: "Ok" },
		},
	];
	useEffect(() => {
		const wizardStr = localStorage.getItem("wizard_input_array");
		let arr: any[] = [];
		if (wizardStr) {
			try {
				arr = JSON.parse(wizardStr);
				setWizardInputs(arr);
				const defaults: Record<string, string> = {};
				arr.forEach((i: any) => {
					if (i.default_value !== undefined) {
						defaults[i.key] = i.default_value;
					} else if (Array.isArray(i.options) && i.options.length > 0) {
						defaults[i.key] = i.options[0];
					} else {
						defaults[i.key] = "";
					}
				});
				setWizardValues(defaults);
			} catch (e) {
				console.error("Failed to parse wizard input array", e);
			}
		}
		if (Array.isArray(arr) && arr.length > 0 && localStorage.getItem("show_wizard") === "true") {
			setShowWizard(true);
		}
	}, []);
	useEffect(() => {
		localStorage.setItem("nodesView", view);
	}, [view]);

	const handleNodesChange = (changes: NodeChange[]) => {
		setRfNodes((nds) => applyNodeChanges(changes, nds));
	};

	// Setup react-hook-form
	const defaultValuesDict: NodeType = {
		name: "",
		is_enabled: true,
		is_starting_node: true,
		schedule_type: "interval",
		crontab_minutes: "*",
		crontab_hours: "*",
		crontab_days_of_month: "*",
		crontab_months_of_year: "*",
		crontab_days_of_week: "*",
		crontab_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,

		interval_every: "30",
		interval_type: "minutes",

		input_data_key_array: [],
		output_data_key_array: [],
		run_after_nodes_array: [],
	};

	const {
		register,
		handleSubmit,
		watch,
		setValue,
		reset,
		control,
		formState: { errors },
	} = useForm({
		defaultValues: defaultValuesDict,
	});
	function getScheduleLabel(n: any) {
		if (n.is_starting_node) {
			if (n.schedule_type === "crontab") return n.crontab_schedule.replace(/\(.*?\)/g, "");
			if (n.schedule_type === "interval") return n.interval_schedule;
			return "Manual / Webhook";
		}
		return `After: ${n.run_after_nodes_array.map((p: any) => p.name).join(", ")}`;
	}

	/** Convert WaveAssist nodes → React-Flow nodes & edges */

	const buildFlow = (nodesArr: any[]): { rfNodes: RFNode[]; rfEdges: RFEdge[] } => {
		const rfNodes: RFNode[] = nodesArr.map((n: any) => ({
			id: n.node_key,
			type: "card", // Use your custom node type if applicable
			draggable: true, // ✅ Optional but explicit

			data: {
				name: n.name,
				node_key: n.node_key,
				is_enabled: n.is_enabled,
				is_premium: n.is_premium, // Include the premium flag from the node data
				scheduleLabel: getScheduleLabel(n),
				onView: () => handleViewCode(n),
				onEdit: () => handleEdit(n),
				onDelete: () => handleDelete(n),
				onRun: () => handleRun(n),
				canRun: n.is_starting_node,
				label: n.name,
			},
			position: { x: 0, y: 0 }, // Placeholder — dagre sets actual values
			style: {
				background: "#232F42",
				border: `2px solid ${n.is_enabled ? "#428d4f" : "#d9534f"}`,
				color: "#fff",
				borderRadius: 8,
				fontSize: 13,
			},
		}));

		const rfEdges: RFEdge[] = nodesArr.flatMap((n: any) =>
			n.run_after_nodes_array.map((parent: any) => ({
				id: `${parent.node_key}->${n.node_key}`,
				source: parent.node_key,
				target: n.node_key,
				animated: true,
				style: {
					stroke: "#49d078", // or your preferred green
					strokeWidth: 1.5,
				},
				markerEnd: { type: "arrowclosed", color: "#49d078" },
			}))
		);

		// Layout with dagre
		const dagreGraph = new dagre.graphlib.Graph();
		dagreGraph.setDefaultEdgeLabel(() => ({}));
		dagreGraph.setGraph({ rankdir: "TB" }); // Top-Bottom layout

		rfNodes.forEach((node) => {
			dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
		});
		rfEdges.forEach((edge) => {
			dagreGraph.setEdge(edge.source, edge.target);
		});

		dagre.layout(dagreGraph);

		// Apply positions
		const layoutedNodes = rfNodes.map((node) => {
			const { x, y } = dagreGraph.node(node.id);
			return {
				...node,
				position: { x, y },
				sourcePosition: Position.Bottom,
				targetPosition: Position.Top,
			};
		});

		return { rfNodes: layoutedNodes, rfEdges };
	};

	const onSubmit = async (data: any) => {
		try {
			if (selected_node_key === "") {
				await createNodeApi(data);
				showToast("Node created successfully.", "success");
			} else {
				await updateNodeApi(selected_node_key, data);
				showToast("Node updated successfully.", "success");
			}
		} catch (error) {
			console.error("FetchNodesApi failed:", error);
			showToast("" + error, "danger");
		}

		setSelectedNodeKey("");
		reset(defaultValuesDict);

		handleClose();
		fetchNodes();
		setShowNodeEditor(false);
	};

	const [nodesArray, setNodesArray] = useState<any[]>([]);
	const [loading, setLoading] = useState(false);

	const { showToast } = useToast();
	const [showCodeModal, setShowCodeModal] = useState(false);
	const [selected_node_key, setSelectedNodeKey] = useState("");
	const [modalCode, setModalCode] = useState('print("Hello, world!")');
	const [showNodeEditor, setShowNodeEditor] = useState(false);

        const premiumBlocked = (): boolean => {
                const isProjectPremium = localStorage.getItem("is_project_premium") === "true";
                const userData = JSON.parse(localStorage.getItem("user_data") || "{}");
                const isUserPremium =
                        localStorage.getItem("is_premium") === "true" || Boolean(userData.is_premium);
                if (isProjectPremium && !isUserPremium) {
                        showToast("Upgrade to edit Premium template", "warning");
                        return true;
                }
                return false;
        };

	const handleClose = () => {
		setSelectedNodeKey("");
		setShowCodeModal(false);
		// setIsOpen(false);
	};

	const handleSave = async () => {
		await updateCodeApi(selected_node_key, modalCode);
		showToast("Code updated successfully.", "success");
		setSelectedNodeKey("");
		handleClose();
		fetchNodes();
	};

	const handleCreateNode = () => {
		if (premiumBlocked()) return;
		reset(defaultValuesDict);
		setSelectedNodeKey("");
		setWebhookUrl("");
		setShowNodeEditor(true);
	};

	// const handleDiagram = async () => {
	// 	setLoading(true);
	// 	var data_dict = await generate_dag_image();
	// 	setLoading(false);
	// 	var s3_key = data_dict.s3_key;
	// 	var url = "https://waveassistapps.s3.amazonaws.com/" + s3_key;
	// 	setUrl(url);
	// 	setIsOpen(true);
	// };

	const handleDownloadCode = () => {
		if (premiumBlocked()) return;
		const zip = new JSZip();
		const config: any = {
			project_key: localStorage.getItem("selected_project_key") || "unknown_project",
			nodes: [],
		};

		nodesArray.forEach((node) => {
			if (node.python_code) {
				const safeFilename = `${node.node_key.replace(/\s+/g, "_")}.py`;
				zip.file(safeFilename, node.python_code);
				config.nodes.push({
					key: node.node_key,
					name: node.name,
					file_name: safeFilename,
				});
			}
		});

		const yamlContent = `project_key: ${config.project_key}
nodes:
${config.nodes
	.map(
		(n: any) => `  - key: ${n.key}
    file_name: ${n.file_name}
    name: ${n.name}`
	)
	.join("\n")}`;

		zip.file("config.yaml", yamlContent);
		zip
			.generateAsync({ type: "blob" })
			.then((content) => {
				saveAs(content, `WaveAssistCode_${config.project_key}.zip`);
			})
			.catch((err) => {
				console.error("Error generating zip file:", err);
			});
	};

	const handleCloseNodeEditor = () => {
		setSelectedNodeKey("");
		setShowNodeEditor(false);
	};

	const generateWebhookUrl = (nodeKey: string): string => {
		const baseUrl = "https://api.waveassist.io/webhook/run";
		const uid = localStorage.getItem("uid");
		const projectKey = localStorage.getItem("selected_project_key");
		const envKey = localStorage.getItem("selected_env_key");

		if (!uid || !projectKey || !envKey || !nodeKey) {
			return ""; // Cannot generate webhook if any piece is missing
		}
		return `${baseUrl}/${uid}/${projectKey}/${nodeKey}/${envKey}/`;
	};

	const generateEmailWebhook = (nodeId: string): string => {
		const uid = localStorage.getItem("uid");
		const projectKey = localStorage.getItem("selected_project_key");
		const projectArray = JSON.parse(localStorage.getItem("projects_array") || "[]");
		const matchingProject = projectArray.find((project: { id: string; project_key: string }) => project.project_key === projectKey);
		const projectId = matchingProject?.id || null;

		const environmentArray = JSON.parse(localStorage.getItem("environment_array") || "[]");
		const envKey = localStorage.getItem("selected_env_key");

		const matchingEnv = environmentArray.find((env: { id: string; key: string }) => env.key === envKey);

		const envId = matchingEnv?.id || null;
		if (!uid || !projectId || !nodeId || !envId) {
			console.warn("Missing required fields for email webhook generation:", { uid, projectId, nodeId, envId });
			return ""; // required fields missing
		}

		// Base64 URL-safe encode
		const b64url = (str: string): string => btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
		console.log("b64url", b64url);
		const uuidNoDash = uid.replace(/-/g, "");
		const emailLocal = [uuidNoDash, b64url(projectId), b64url(nodeId), b64url(envId)].join(".");

		if (emailLocal.length > 64) {
			console.warn("Email local-part exceeds 64 characters.");
			return "";
		}

		return `${emailLocal}@trigger.waveassist.io`;
	};

	const handleEdit = (node: any) => {
		if (premiumBlocked()) return;
		if (node.crontab_schedule && node.crontab_schedule.includes("m/h/dM/MY/d")) {
			const [minute, hour, dayOfMonth, month, dayOfWeek, , timezone] = node.crontab_schedule.split(" ");
			Object.assign(node, {
				crontab_minutes: minute,
				crontab_hours: hour,
				crontab_days_of_month: dayOfMonth,
				crontab_months_of_year: month,
				crontab_days_of_week: dayOfWeek,
				crontab_timezone: timezone,
			});
		}

		if (node.interval_schedule) {
			const [, interval_every, interval_type] = node.interval_schedule.split(" ");
			Object.assign(node, {
				interval_every: interval_every,
				interval_type: interval_type,
			});
		}

		reset(node);
		setSelectedNodeKey(node.node_key);
		setWebhookUrl(generateWebhookUrl(node.node_key));
		setEmailWebhook(generateEmailWebhook(node.id));
		setShowNodeEditor(true);
	};

	const editorOptions = {
		selectOnLineNumbers: true,
		roundedSelection: false,
		readOnly: false,
		automaticLayout: true,
		language: "python", // Set the language to Python for syntax highlighting
		theme: "vs-dark", // Use a dark theme
		mode: "python",
		quickSuggestions: true, // Enable quick suggestions
	};

	const fetchNodes = async () => {
		try {
			const data = await fetchNodesApi();
			console.log("API Response:", data); // Debug log to see the API response

			// Ensure project premium status is set in localStorage
			const projectData = JSON.parse(localStorage.getItem("selected_project") || "{}");
			if (projectData && projectData.is_premium !== undefined) {
				localStorage.setItem("is_project_premium", projectData.is_premium ? "true" : "false");
			} else if (data.is_project_premium !== undefined) {
				localStorage.setItem("is_project_premium", data.is_project_premium ? "true" : "false");
			}

			var nodes_array = data.node_array;
			console.log("Nodes array:", nodes_array); // Debug log to see the nodes array
			//Sort to keep the starting node at the top
			nodes_array.sort((a: any, b: any) => {
				if (a.is_starting_node && !b.is_starting_node) return -1;
				if (!a.is_starting_node && b.is_starting_node) return 1;
				return 0; // Keep original order for other nodes
			});
			setNodesArray(nodes_array);
			const { rfNodes, rfEdges } = buildFlow(nodes_array);
			setRfNodes(rfNodes);
			setRfEdges(rfEdges);
			const startNode = nodes_array.find((n: any) => n.is_starting_node);
			setStartingNodeKey(startNode ? startNode.node_key : nodes_array[0]?.node_key || null);
			const is_template_run = localStorage.getItem("is_template_run");
			const tourCompleted = localStorage.getItem("run_node_tour") === "true";
			if (!tourCompleted && is_template_run === "true") {
				setRunTour(true);
				localStorage.setItem("run_node_tour", "true");
			}
		} catch (error) {
			console.error("FetchNodesApi failed:", error);
			showToast("Something went wrong with loading Nodes, please try again.", "danger");
		}
	};

	const gridOptions: GridOptions = {
		suppressCellFocus: true,
	};

	useEffect(() => {
		fetchNodes();
	}, [shouldRefresh]);

	const handleViewCode = (node: any) => {
		if (premiumBlocked()) return;
		setModalCode(node.python_code);
		setSelectedNodeKey(node.node_key);
		setShowCodeModal(true);
	};

	const handleDelete = async (node: any) => {
		if (premiumBlocked()) return;
		//ask for confirmation
		const confirmDelete = window.confirm("Are you sure you want to delete this node? This action cannot be undone.");
		if (!confirmDelete) {
			return;
		}
		try {
			await deleteNodeApi(node.node_key);
			showToast("Node deleted successfully.", "success");
		} catch (error) {
			console.error("DeleteNodeAPI failed:", error);
			showToast("" + error, "danger");
		}
		fetchNodes();
	};

	const handleRun = async (node: any) => {
		const current_env = localStorage.getItem("selected_env_key");
		if (!current_env) {
			showToast("Please select an environment to run the node.", "danger");
			return;
		}
		var confirm_message = "Do you want to run this and all connected nodes in the " + current_env + " environment?";
		const confirmRun = window.confirm(confirm_message);
		if (!confirmRun) {
			return;
		}
		try {
			setLoading(true);
			await runDAGApi(node.node_key, current_env);
			showToast("Node & connected nodes started running successfully.", "success");
		} catch (error) {
			console.error("Running nodes failed:", error);
			showToast("" + error, "danger");
		} finally {
			setLoading(false);
		}
		fetchNodes();
	};

	const ViewCodeButton = (params: any) => {
		// Debug log to see the node data
		console.log("ViewCode Node data:", params.data);

		// Check if the project is premium and if the user has premium access
		const isProjectPremium = localStorage.getItem("is_project_premium") === "true";
                const userData = JSON.parse(localStorage.getItem("user_data") || "{}");
                const isUserPremium =
                        localStorage.getItem("is_premium") === "true" || Boolean(userData.is_premium);
                const isDisabled = isProjectPremium && !isUserPremium;

		// Debug log to see the premium status
		console.log(
			`ViewCode Node: ${params.data.name}, isProjectPremium: ${isProjectPremium}, isUserPremium: ${isUserPremium}, isDisabled: ${isDisabled}`
		);

                return (
                        <button
                                className="btn btn-outline-success btn-sm"
                                disabled={isDisabled}
                                onClick={() => {
                                        if (!isDisabled) handleViewCode(params.data);
                                }}
                                title={isDisabled ? "Premium feature - upgrade to access" : "View node code"}
                        >
                                View Code
                        </button>
                );
        };

	const toggleView = () => {
		setView(view === "flow" ? "table" : "flow");
	};

	const handleWizardInputChange = (key: string, value: string) => {
		setWizardValues((prev) => ({ ...prev, [key]: value }));
	};

	const handleRunAndDeploy = async () => {
		setProcessingWizard(true);
		try {
			for (const input of wizardInputs) {
				await setDataForKeyApi(wizardValues[input.key], input.key, "string");
			}
			if (startingNodeKey) {
				const env = localStorage.getItem("selected_env_key") || "";
				await runDAGApi(startingNodeKey, env);
			}
			await deployProjectApi("1.0.0");
			setWizardDone(true);
			localStorage.setItem("show_wizard", "false");
		} catch (error) {
			console.error("Wizard run failed:", error);
			showToast("" + error, "danger");
		} finally {
			setProcessingWizard(false);
		}
	};

	const ActionButtons = (params: any) => {
		// Debug log to see the node data
		console.log("Node data:", params.data);

		// Check if the project is premium and if the user has premium access
                const isProjectPremium = localStorage.getItem("is_project_premium") === "true";
                const userData = JSON.parse(localStorage.getItem("user_data") || "{}");
                const isUserPremium =
                        localStorage.getItem("is_premium") === "true" || Boolean(userData.is_premium);
                const isDisabled = isProjectPremium && !isUserPremium;

		// Debug log to see the premium status
		console.log(`Node: ${params.data.name}, isProjectPremium: ${isProjectPremium}, isUserPremium: ${isUserPremium}, isDisabled: ${isDisabled}`);

		return (
			<div>
                                <Button
                                        variant="dark"
                                        size="sm"
                                        disabled={isDisabled}
                                        onClick={() => {
                                                if (!isDisabled) handleEdit(params.data);
                                        }}
                                        title={isDisabled ? "Premium feature - upgrade to access" : "Edit node"}
                                >
                                        <i className="bi bi-pencil"></i>
                                </Button>{" "}
                                <Button
                                        variant="danger"
                                        size="sm"
                                        disabled={isDisabled}
                                        onClick={() => {
                                                if (!isDisabled) handleDelete(params.data);
                                        }}
                                        title={isDisabled ? "Premium feature - upgrade to access" : "Delete node"}
                                >
                                        <i className="bi bi-trash"></i>
                                </Button>{" "}
				{params.data.is_starting_node && (
					<Button variant="success" size="sm" onClick={() => handleRun(params.data)} title="Run node">
						<i className="bi bi-play">Run</i>
					</Button>
				)}
				{!params.data.is_starting_node && (
					<Button variant="secondary" size="sm" disabled>
						<i className="bi bi-play"></i>
					</Button>
				)}
			</div>
		);
	};

	const formatSchedule = (data: any) => {
		if (data.is_starting_node) {
			if (data.schedule_type === "crontab") {
				const cleanedCrontabSchedule = data.crontab_schedule.replace(/\(.*?\)/g, "");
				return (
					<div>
						<span className="badge badge-important">Starting Node</span> <span className="badge badge-primary">Cron</span>{" "}
						<span className="badge badge-secondary">{cleanedCrontabSchedule}</span>
					</div>
				);
			} else if (data.schedule_type === "interval") {
				return (
					<div>
						<span className="badge badge-important">Starting Node</span>
						<span className="badge badge-primary">Interval</span> <span className="badge badge-secondary">{data.interval_schedule}</span>
					</div>
				);
			} else if (data.schedule_type === "none") {
				return (
					<div>
						<span className="badge badge-important">Starting Node</span> <span className="badge badge-primary">Manual/Webhook Only</span>
					</div>
				);
			}
		} else {
			return (
				<div>
					<span className="badge badge-primary">Runs After</span>{" "}
					{data.run_after_nodes_array.map((node: any) => (
						<span key={node.name} className="badge badge-secondary">
							{node.name}
						</span>
					))}
				</div>
			);
		}
		return <div></div>;
	};

	const defaultColDef = {
		autoHeight: true,
		wrapText: true,
		enableCellChangeFlash: true,
		editable: false,
		cellClass: "ag-cell",
	};

	const columnDefs = [
		{ headerName: "Name", field: "name", flex: 1, minWidth: 120, resizable: true }, // Expands to fill space
		// node_key
		{
			headerName: "Node Key",
			field: "node_key",
			cellRenderer: (params: any) => <span className="badge badge-secondary">{params.value}</span>,
			flex: 1,
			minWidth: 120, // Prevents shrinking too much
			resizable: true,
		},
		{
			headerName: "Status",
			field: "is_enabled",
			cellRenderer: (params: any) => (
				<span className={`badge ${params.value ? "badge-primary" : "badge-danger"}`}>{params.value ? "Enabled" : "Disabled"}</span>
			),
			width: 120,
			minWidth: 80, // Prevents shrinking too much
			resizable: true,
		},
		{
			headerName: "Scheduled",
			width: 200,
			minWidth: 150,
			resizable: true,
			cellRenderer: (params: any) => formatSchedule(params.data),
		},
		{ headerName: "Code", cellRenderer: ViewCodeButton, width: 140, minWidth: 120, resizable: true },
		{ headerName: "Actions", cellRenderer: ActionButtons, width: 180, minWidth: 140, resizable: true },
	];

	const isStartingNode = watch("is_starting_node");
	const scheduleType = watch("schedule_type") || "interval";

	return (
		<div className="main-container">
			{loading && (
				<div className="my-3">
					<Spinner animation="border" role="status" variant="success">
						<span className="visually-hidden">Loading...</span>
					</Spinner>
				</div>
			)}

			<div className="mt-3">
				<div className="d-flex justify-content-start align-items-center mb-3">
					<h3 className="translucent_white">Nodes</h3>
					<div className="ms-auto d-flex">
						<Button variant="dark" onClick={toggleView} className="ms-2" aria-label="Toggle view">
							{view === "flow" ? (
								<span className="bi bi-table">{!isMobile && <>&nbsp; Table View</>}</span>
							) : (
								<span className="bi bi-diagram-2">{!isMobile && <> Flow View</>}</span>
							)}
						</Button>
						<Button variant="dark" onClick={handleCreateNode} className="ms-2">
							<span className="bi bi-plus-lg">{!isMobile && <> Add Node</>}</span>
						</Button>
						<Button variant="dark" onClick={handleDownloadCode} className="ms-2">
							<span className="bi bi-cloud-download">{/* No text for download, just icon */}</span>
						</Button>
					</div>
				</div>

				{view === "table" ? (
					<NodeTableView rowData={nodesArray} columnDefs={columnDefs} gridOptions={gridOptions} defaultColDef={defaultColDef} />
				) : (
					<Suspense fallback={<Spinner animation="border" />}>
						<NodeFlowView nodes={rfNodes} edges={rfEdges} onNodesChange={handleNodesChange} />
					</Suspense>
				)}
			</div>

			{/* <Modal show={isOpen} onHide={handleClose} size="lg" centered>
				<Modal.Header closeButton>
					<Modal.Title>Nodes Flow</Modal.Title>
				</Modal.Header>
				<Modal.Body style={{ padding: "30px" }}>
					<div style={{ width: "100%", height: "100%", display: "flex", justifyContent: "center", alignItems: "center" }}>
						<img src={url} alt="Generated" style={{ maxWidth: "100%", maxHeight: "100%", width: "auto", height: "auto" }} />
					</div>
				</Modal.Body>
			</Modal> */}

			<Modal show={showCodeModal} onHide={handleClose} size="lg" centered>
				<Modal.Header>
					<Modal.Title>Edit Code</Modal.Title>
				</Modal.Header>
				<Modal.Body>
					<Editor
						width="100%"
						height="500px"
						theme="vs-dark"
						defaultLanguage="python"
						value={modalCode}
						options={editorOptions}
						onChange={(newValue: any) => setModalCode(newValue)}
					/>
				</Modal.Body>
				<Modal.Footer>
					<Button variant="secondary" onClick={handleClose}>
						Close
					</Button>
					<Button variant="primary" onClick={handleSave}>
						Save
					</Button>
				</Modal.Footer>
			</Modal>

			<Modal show={showNodeEditor} onHide={handleCloseNodeEditor} size="lg" centered>
				<Modal.Header closeButton>
					<Modal.Title>{selected_node_key === "" ? "Add Node" : "Edit Node"}</Modal.Title>
				</Modal.Header>
				<Modal.Body>
					<Form onSubmit={handleSubmit(onSubmit)}>
						<div className="d-flex align-items-center mb-3">
							{/* Node Name */}
							<Form.Group controlId="name" className="flex-grow-1 me-4">
								<Form.Label>Node Name</Form.Label>
								<Form.Control
									type="text"
									className="w-100"
									style={{ flexBasis: "50%" }}
									{...register("name", { required: "Node name is required" })}
								/>
								{errors.name && <p className="text-danger">{errors.name.message}</p>}
							</Form.Group>

							{/* Status */}
							<Form.Group controlId="is_enabled" className="me-2">
								<Form.Label>Status</Form.Label>
								<DropdownButton
									variant="secondary"
									title={watch("is_enabled") ? "Enabled" : "Disabled"}
									id="statusDropdown"
									onSelect={(selected) => setValue("is_enabled", selected === "enabled")}>
									<Dropdown.Item eventKey="enabled">Enabled</Dropdown.Item>
									<Dropdown.Item eventKey="disabled">Disabled</Dropdown.Item>
								</DropdownButton>
							</Form.Group>
						</div>
						<hr />

						{/* Starting Node */}
						<Form.Group controlId="is_starting_node" className="mb-3">
							<Form.Label>Is this a starting node: </Form.Label>
							<DropdownButton
								variant="secondary"
								className="mt-2"
								title={watch("is_starting_node") ? "Yes" : "No"}
								id="isStartingNodeDropdown"
								onSelect={(selected) => setValue("is_starting_node", selected === "yes")}>
								<Dropdown.Item eventKey="yes">Yes</Dropdown.Item>
								<Dropdown.Item eventKey="no">No</Dropdown.Item>
							</DropdownButton>
						</Form.Group>

						{/* Conditional Rendering Based on Starting Node */}
						{isStartingNode ? (
							<>
								<hr />
								{/* Schedule Type */}
								<Form.Label>Schedule Type: </Form.Label>
								<Form.Group controlId="schedule_type">
									<DropdownButton
										variant="secondary"
										title={scheduleType === "interval" ? "Interval" : scheduleType === "crontab" ? "Cron" : "Manual / Webhook Only"}
										id="scheduleTypeDropdown"
										onSelect={(selected) => setValue("schedule_type", selected!)}>
										<Dropdown.Item eventKey="interval">Interval</Dropdown.Item>
										<Dropdown.Item eventKey="crontab">Cron</Dropdown.Item>
										<Dropdown.Item eventKey="none">Manual/Webhook Only</Dropdown.Item>
									</DropdownButton>
								</Form.Group>
								<hr />

								{/* Interval Schedule */}
								{scheduleType === "interval" && (
									<div>
										<Form.Group controlId="interval_every" className="d-flex align-items-center">
											<Form.Label className="me-2">Every</Form.Label>
											<Form.Control type="text" className="w-25 me-2" {...register("interval_every")} />
											<DropdownButton
												variant="secondary"
												title={watch("interval_type") || "Select Interval Type"}
												id="intervalTypeDropdown"
												onSelect={(selected) => setValue("interval_type", selected!)}>
												<Dropdown.Item eventKey="days">days</Dropdown.Item>
												<Dropdown.Item eventKey="hours">hours</Dropdown.Item>
												<Dropdown.Item eventKey="minutes">minutes</Dropdown.Item>
												<Dropdown.Item eventKey="seconds">seconds</Dropdown.Item>
												<Dropdown.Item eventKey="microseconds">microseconds</Dropdown.Item>
											</DropdownButton>
										</Form.Group>
									</div>
								)}

								{/* Cron Schedule */}
								{scheduleType === "crontab" && (
									<div className="row">
										{/* Minute (m) */}
										<div className="col-md-6">
											<Form.Group controlId="crontab_minutes">
												<Form.Label>Minute (m)</Form.Label>
												<Form.Control type="text" className="w-100" {...register("crontab_minutes")} />
											</Form.Group>
										</div>

										{/* Hour (h) */}
										<div className="col-md-6">
											<Form.Group controlId="crontab_hours">
												<Form.Label>Hour (h)</Form.Label>
												<Form.Control type="text" className="w-100" {...register("crontab_hours")} />
											</Form.Group>
										</div>

										{/* Day of Month (dM) */}
										<div className="col-md-6">
											<Form.Group controlId="crontab_days_of_month">
												<Form.Label>Day of Month (dM)</Form.Label>
												<Form.Control type="text" className="w-100" {...register("crontab_days_of_month")} />
											</Form.Group>
										</div>

										{/* Month of Year (MY) */}
										<div className="col-md-6">
											<Form.Group controlId="crontab_months_of_year">
												<Form.Label>Month of Year (MY)</Form.Label>
												<Form.Control type="text" className="w-100" {...register("crontab_months_of_year")} />
											</Form.Group>
										</div>

										{/* Day of Week (d) */}
										<div className="col-md-6">
											<Form.Group controlId="crontab_days_of_week">
												<Form.Label>Day of Week (d)</Form.Label>
												<Form.Control type="text" className="w-100" {...register("crontab_days_of_week")} />
											</Form.Group>
										</div>

										{/* Timezone */}
										<div className="col-md-6">
											<Form.Group controlId="crontab_timezone">
												<Form.Label>Timezone</Form.Label>
												<DropdownButton
													variant="secondary"
													title={watch("crontab_timezone") || "Select Timezone"}
													id="timezoneDropdown"
													onSelect={(selected) => setValue("crontab_timezone", selected!)}>
													{timezones.map((timezone, index) => (
														<Dropdown.Item key={index} eventKey={timezone}>
															{timezone}
														</Dropdown.Item>
													))}
												</DropdownButton>
											</Form.Group>
										</div>
									</div>
								)}

								<hr />
								{webhookUrl && (
									<Form.Group className="mb-4">
										{/* Toggle header */}
										<div
											onClick={() => setShowWebhook((f) => !f)}
											style={{
												cursor: "pointer",
												display: "inline-flex",
												alignItems: "center",
												userSelect: "none",
											}}>
											<i className={`bi me-2 ${showWebhook ? "bi-caret-down-fill" : "bi-caret-right-fill"}`} />
											<strong>Webhook URL</strong>
										</div>

										{/* Collapsible content */}
										<Collapse in={showWebhook}>
											<div>
												<span className="trigger-text">Send a POST request to this URL to trigger the workflow programmatically.</span>

												<div className="mt-2 p-3 bg-dark text-white rounded" style={{ overflow: "hidden" }}>
													<Badge bg="secondary">POST</Badge>
													<span className="ms-2 flex-grow-1" style={{ wordBreak: "break-all", fontSize: "0.9rem" }}>
														{webhookUrl}
													</span>
													<Button
														variant="link"
														className="p-0 ms-3 text-white"
														onClick={() => {
															navigator.clipboard.writeText(webhookUrl);
															setCopied(true);
															setTimeout(() => setCopied(false), 2000); // reset after 2 sec
														}}
														aria-label="Copy URL">
														{copied ? (
															<i className="bi bi-check-lg"></i> // checkmark after copy
														) : (
															<i className="bi bi-clipboard"></i> // normal clipboard icon
														)}
													</Button>
												</div>
											</div>
										</Collapse>
									</Form.Group>
								)}
								{emailWebhook && (
									<Form.Group className="mb-4">
										{/* Toggle header */}
										<div
											onClick={() => setShowEmailWebhook((f) => !f)}
											style={{
												cursor: "pointer",
												display: "inline-flex",
												alignItems: "center",
												userSelect: "none",
											}}>
											<i className={`bi me-2 ${showEmailWebhook ? "bi-caret-down-fill" : "bi-caret-right-fill"}`} />
											<strong>Trigger Email</strong>
										</div>

										{/* Collapsible content */}
										<Collapse in={showEmailWebhook}>
											<div className="mt-2 p-3 bg-dark text-white rounded" style={{ overflow: "hidden" }}>
												<span className="trigger-text">Sending any email to this address will trigger the workflow.</span>
												<Badge bg="secondary">EMAIL TO: </Badge>
												<span className="ms-2 flex-grow-1" style={{ wordBreak: "break-all", fontSize: "0.9rem" }}>
													{emailWebhook}
												</span>
												<Button
													variant="link"
													className="p-0 ms-3 text-white"
													onClick={() => {
														navigator.clipboard.writeText(emailWebhook);
														setCopied(true);
														setTimeout(() => setCopied(false), 2000); // reset after 2 sec
													}}
													aria-label="Copy URL">
													{copied ? (
														<i className="bi bi-check-lg"></i> // checkmark after copy
													) : (
														<i className="bi bi-clipboard"></i> // normal clipboard icon
													)}
												</Button>
											</div>
										</Collapse>
									</Form.Group>
								)}
							</>
						) : (
							<>
								<hr />
								{/* Run After Nodes */}
								<Form.Label>Run After Nodes:</Form.Label>
								<div className="row">
									{nodesArray.map((node) => (
										<div className="col-6" key={node.node_key}>
											<Form.Group controlId={`node-${node.node_key}`}>
												<Controller
													control={control}
													name="run_after_nodes_array"
													render={({ field }) => {
														const isChecked = field.value.some((item: any) => item.node_key === node.node_key);
														return (
															<Form.Check
																type="checkbox"
																label={node.name}
																checked={isChecked}
																onChange={(e) => {
																	const newValue = e.target.checked
																		? [...field.value, node]
																		: field.value.filter((item: any) => item.node_key !== node.node_key);
																	field.onChange(newValue);
																}}
															/>
														);
													}}
												/>
											</Form.Group>
										</div>
									))}
								</div>
								<br></br>
							</>
						)}

						{/* Modal Footer */}
						<Modal.Footer>
							<Button variant="secondary" onClick={handleCloseNodeEditor}>
								Close
							</Button>
							<Button variant="primary" type="submit">
								Save
							</Button>
						</Modal.Footer>
					</Form>
				</Modal.Body>
			</Modal>

			<Modal show={showWizard} backdrop="static" keyboard={false} centered>
				<Modal.Header>
					<Modal.Title>Setup Wizard</Modal.Title>
				</Modal.Header>
				<Modal.Body>
					{wizardDone ? (
						<div className="text-center">
							<span className="badge bg-success mb-2">Deployed</span>
							<p>🎉 Your assistant was started and deployed! 🎉</p>
						</div>
					) : (
						<Form>
							{wizardInputs.map((inp) => (
								<Form.Group className="mb-3" key={inp.key}>
									<Form.Label>{inp.key}</Form.Label>
									{Array.isArray(inp.options) && inp.options.length > 0 ? (
										<Form.Select value={wizardValues[inp.key] || inp.options[0]} onChange={(e) => handleWizardInputChange(inp.key, e.target.value)}>
											{inp.options.map((opt: string, idx: number) => (
												<option key={idx} value={opt}>
													{opt}
												</option>
											))}
										</Form.Select>
									) : (
										<Form.Control
											type="text"
											value={wizardValues[inp.key] || ""}
											onChange={(e) => handleWizardInputChange(inp.key, e.target.value)}
										/>
									)}
									{inp.helper_message && <Form.Text className="text-secondary">{inp.helper_message}</Form.Text>}
								</Form.Group>
							))}
						</Form>
					)}
				</Modal.Body>
				<Modal.Footer>
					{wizardDone ? (
						<Button variant="primary" onClick={() => navigate("/manage/runs")}>
							View Runs
						</Button>
					) : (
						<Button variant="success" className="w-100" onClick={handleRunAndDeploy} disabled={processingWizard}>
							{processingWizard ? "Processing..." : "Run and Deploy"}
						</Button>
					)}
				</Modal.Footer>
			</Modal>

			<Joyride
				steps={steps}
				run={runTour}
				showProgress
				showSkipButton
				continuous
				styles={{
					options: {
						arrowColor: "#0D1B2A",
						backgroundColor: "#0D1B2A",
						primaryColor: "#2ECC71",
						textColor: "#FFFFFF",
						width: 300,
						zIndex: 10000,
					},
					tooltipContainer: {
						textAlign: "left",
						padding: "16px",
						borderRadius: "12px",
					},
					buttonNext: {
						backgroundColor: "#2ECC71",
						color: "#000",
					},
					buttonBack: {
						color: "#bbb",
						marginRight: 8,
					},
					buttonClose: {
						color: "#aaa",
					},
				}}
				callback={(data) => {
					if (["finished", "skipped"].includes(data.status)) {
						setRunTour(false);
						localStorage.setItem("create_node_tour_completed", "true");
					}
				}}
			/>
		</div>
	);
};

export default NodesComponent;
