import React, { useEffect, useState } from "react";
import { Navbar, Nav, Button, Modal } from "react-bootstrap";
import "./navbar.css";
import DarkDropdown from "./dark_dropdown";
import { fetchEnvironmentsApi, deployProjectApi } from "../services/navbar_services";
import { useToast } from "./toast_context";
import { useRefresh } from "./RefreshContext"; // Import the custom hook
import { usePostHog } from "posthog-js/react";
import WaveAssistLogo from "../assets/Logo/GreenLogo_Full_white_no_w.png";
interface NavbarProps {
	onToggleSidebar?: () => void;
}

const NavbarComponent: React.FC<NavbarProps> = ({ onToggleSidebar }) => {
	const { showToast } = useToast();
	const { triggerRefresh } = useRefresh();
	const posthog = usePostHog();

	const [environmentArray, setEnvironmentArray] = useState<{ name: string; key: string }[]>([]);
	const envItems = environmentArray.map((env) => env.name);
	const envKeys = environmentArray.map((env) => env.key);
	const [showModal, setShowModal] = useState(false);
	const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

	useEffect(() => {
		const handleResize = () => setIsMobile(window.innerWidth < 768);
		window.addEventListener("resize", handleResize);
		return () => window.removeEventListener("resize", handleResize);
	}, []);

	const selectedProjectKey = localStorage.getItem("selected_project_key");
	const projectsArray = JSON.parse(localStorage.getItem("projects_array") || "[]");
	const projectKeys = projectsArray.map((project: any) => project.project_key);
	const projectNames = projectsArray.map((project: any) => project.name + " - " + project.project_key);
	const [selectedEnvName, setSelectedEnvName] = useState("Default");
	const [versionCode, setVersionCode] = useState("1.0.0");

	// Simple checks for premium status
	const isProjectPremium = localStorage.getItem("is_project_premium") === "true";
	const userData = JSON.parse(localStorage.getItem("user_data") || "{}");
	const isUserPremium = localStorage.getItem("is_premium") === "true" || Boolean(userData.is_premium);

	// Get plan name to determine if user is on operator plan
	const currentPlanName = localStorage.getItem("plan_name") || "operator";
	const isOperatorPlan = currentPlanName === "operator";

	const showDeployButton = !(isProjectPremium && !isUserPremium) && !isOperatorPlan;

	useEffect(() => {
		fetchEnvironments();
	}, []);

	const fetchEnvironments = async () => {
		try {
			const data = await fetchEnvironmentsApi();
			setEnvironmentArray(data.environment_array);
			localStorage.setItem("environment_array", JSON.stringify(data.environment_array));
			//Check if selected_env_key is present in the environment array
			const selectedEnvKey = localStorage.getItem("selected_env_key");
			if (selectedEnvKey) {
				var selectedEnv = data.environment_array.find((env: any) => env.key === selectedEnvKey);
				if (selectedEnv) {
					setSelectedEnvName(selectedEnv.name);
					return;
				}
			}
			//Set selected_env_key to the first environment in the array if any
			if (data.environment_array.length > 0) {
				selectedEnv = data.environment_array[0];
				localStorage.setItem("selected_env_key", selectedEnv.key);
				setSelectedEnvName(selectedEnv.name);
			}
		} catch (error) {
			console.error("fetchEnvironments failed:", error);
			showToast("Something went wrong with loading environments, please try again.", "danger");
		}
	};

	const handleProjectChange = async (_project_name: string, project_key: string) => {
		localStorage.setItem("selected_project_key", project_key);
		localStorage.setItem("selected_env_key", project_key + "_default");

		// Retrieve the selected project's details so we can update
		// the premium status flag used throughout the app
		const selectedProject = projectsArray.find((p: any) => p.project_key === project_key);
		if (selectedProject) {
			localStorage.setItem("is_project_premium", selectedProject.is_premium ? "true" : "false");
			localStorage.setItem("selected_project", JSON.stringify(selectedProject));
		} else {
			localStorage.removeItem("is_project_premium");
			localStorage.removeItem("selected_project");
		}

		// Track environment list refresh due to project switch and pageview context
		try {
			posthog?.capture("project_switched", {
				project_id: project_key,
				page_category: "project_detail",
			});
			posthog?.capture("$pageview", {
				page_category: "project_detail",
				project_id: project_key,
				environment: localStorage.getItem("selected_env_key") || undefined,
			});
		} catch (_err) {}

		await fetchEnvironments();
		triggerRefresh(); // Trigger a refresh
	};

	const handleEnvChange = (env_name: string, env_key: string) => {
		localStorage.setItem("selected_env_key", env_key);
		setSelectedEnvName(env_name);
		// Track environment switched
		try {
			posthog?.capture("environment_switched", {
				project_id: localStorage.getItem("selected_project_key") || undefined,
				environment: env_key,
				page_category: "project_detail",
			});
		} catch (_err) {}
		triggerRefresh(); // Trigger a refresh
	};

	const getDefaultProjectName = (): string => {
		const selectedProject = projectsArray.find((project: any) => project.project_key === selectedProjectKey);
		return selectedProject ? selectedProject.name + " - " + selectedProject.project_key : "Select Project";
	};

	const handleOpenModal = () => {
		setShowModal(true);
	};

	const handleCloseModal = () => {
		setVersionCode("");
		setShowModal(false);
	};

	const handleDeployProject = async () => {
		try {
			// Add your deploy project logic here
			console.log("Deploying project with version code:", versionCode);
			await deployProjectApi(versionCode);
			showToast("Project deployed successfully", "success");
			try {
				posthog?.capture("deployment_triggered", {
					project_id: localStorage.getItem("selected_project_key") || undefined,
					environment: localStorage.getItem("selected_env_key") || undefined,
					version: versionCode,
				});
			} catch (_err) {}
			handleCloseModal();
		} catch (error) {
			console.error("Deploy Project Failed:", error);
			showToast("" + error, "danger");
		}
	};

	return (
		<Navbar variant="dark" expand="lg" className="px-3 navbar-main">
			{isMobile ? (
				<>
					<Button variant="dark" className="me-2 text-white navbar-hamburger" onClick={onToggleSidebar}>
						<i className="bi bi-list"></i>
					</Button>
					<div className="navbar-logo-container flex-shrink-1">
						<img src={WaveAssistLogo} alt="WaveAssist" className="navbar-logo" style={{ height: "24px", maxWidth: "150px", width: "auto" }} />
					</div>
					<div className="ms-auto d-flex align-items-center flex-shrink-0 navbar-actions">
						{!isOperatorPlan && (
							<DarkDropdown
								items={envItems}
								keys={envKeys}
								defaultText={selectedEnvName}
								headerText="Select Environment"
								onItemSelect={handleEnvChange}
								icon="bi-stack"
							/>
						)}

						{showDeployButton && (
							<Button variant="dark" className="ms-2 icon-dropdown-btn text-white" onClick={handleOpenModal}>
								<i className="bi bi-cloud-arrow-up-fill"></i>
							</Button>
						)}
						{isOperatorPlan && !isMobile && (
							<Button variant="outline-secondary" onClick={() => window.open("https://waveassist.io/pricing", "_blank")}>
								<i className="bi bi-star"></i>
							</Button>
						)}
					</div>
				</>
			) : (
				<>
					<Navbar.Toggle aria-controls="navbar-nav" />
					<Navbar.Collapse id="navbar-nav">
						<Nav className="me-auto">
							<DarkDropdown
								items={projectNames}
								keys={projectKeys}
								defaultText={getDefaultProjectName()}
								headerText="Select Assistant"
								onItemSelect={handleProjectChange}
							/>
							{!isOperatorPlan && (
								<DarkDropdown
									items={envItems}
									keys={envKeys}
									defaultText={selectedEnvName}
									headerText="Select Environment"
									onItemSelect={handleEnvChange}
								/>
							)}
						</Nav>
						<Nav className="ms-auto">
							{showDeployButton && (
								<Button variant="dark" className="px-3 text-white" onClick={handleOpenModal}>
									<i className="bi bi-cloud-arrow-up-fill me-2"></i>
									Deploy
								</Button>
							)}
							{isOperatorPlan && (
								<Button variant="outline-secondary" onClick={() => window.open("https://waveassist.io/pricing", "_blank")}>
									<i className="bi bi-star me-2"></i>
									Upgrade
								</Button>
							)}
						</Nav>
					</Navbar.Collapse>
				</>
			)}

			<Modal show={showModal} onHide={handleCloseModal}>
				<Modal.Header closeButton>
					<Modal.Title className="modal-title">Deploy Project - {selectedEnvName} Environment</Modal.Title>
				</Modal.Header>
				<Modal.Body>
					<div className="mb-3">
						<label htmlFor="projectNameInput" className="form-label">
							Version Code
						</label>
						<input type="text" className="form-control" id="projectNameInput" value={versionCode} onChange={(e) => setVersionCode(e.target.value)} />
						<div id="projectNameHelp" className="form-text model-text">
							Deploying this project will stop existing deployments and replace them with this version.
						</div>
					</div>
				</Modal.Body>
				<Modal.Footer>
					<Button variant="secondary" onClick={handleCloseModal}>
						Close
					</Button>
					<Button variant="primary" onClick={handleDeployProject}>
						Deploy
					</Button>
				</Modal.Footer>
			</Modal>
		</Navbar>
	);
};

export default NavbarComponent;
