import React, { useEffect, useState } from "react";
import { Navbar, Nav, Button, Modal } from "react-bootstrap";
import "./navbar.css";
import DarkDropdown from "./dark_dropdown";
import { fetchEnvironmentsApi, deployProjectApi } from "../services/navbar_services";
import { useToast } from "./toast_context";
import { useRefresh } from "./RefreshContext"; // Import the custom hook
const NavbarComponent: React.FC = () => {
	const { showToast } = useToast();
	const { triggerRefresh } = useRefresh();

	const [environmentArray, setEnvironmentArray] = useState<{ name: string; key: string }[]>([]);
	const envItems = environmentArray.map((env) => env.name);
	const envKeys = environmentArray.map((env) => env.key);
	const [showModal, setShowModal] = useState(false);

	const selectedProjectKey = localStorage.getItem("selected_project_key");
	const projectsArray = JSON.parse(localStorage.getItem("projects_array") || "[]");
	const projectKeys = projectsArray.map((project: any) => project.project_key);
	const projectNames = projectsArray.map((project: any) => project.name + " - " + project.project_key);
	const [selectedEnvName, setSelectedEnvName] = useState("Default");
	const [versionCode, setVersionCode] = useState("1.0.0");

	useEffect(() => {
		fetchEnvironments();
	}, []);

	const fetchEnvironments = async () => {
		try {
			const data = await fetchEnvironmentsApi();
			setEnvironmentArray(data.environment_array);
			localStorage.setItem("setEnvironmentArray", JSON.stringify(data.environment_array));

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
		await fetchEnvironments();
		triggerRefresh(); // Trigger a refresh
	};

	const handleEnvChange = (env_name: string, env_key: string) => {
		localStorage.setItem("selected_env_key", env_key);
		setSelectedEnvName(env_name);
		triggerRefresh(); // Trigger a refresh
	};

	const getDefaultProjectName = (): string => {
		const selectedProject = projectsArray.find((project: any) => project.project_key === selectedProjectKey);
		return selectedProject ? selectedProject.name + " - " + selectedProject.project_key : "Select Project";
	};

	// const getDefaultEnvironmentName = (): string => {
	// 	const selectedEnvKey = localStorage.getItem("selected_env_key");
	// 	const selectedEnv = environmentArray.find((env: any) => env.key === selectedEnvKey);
	// 	console.log(selectedEnvKey, selectedEnv, environmentArray);
	// 	return selectedEnv ? selectedEnv.name : "Select Environment";
	// };

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
			handleCloseModal();
		} catch (error) {
			console.error("Deploy Project Failed:", error);
			showToast("" + error, "danger");
		}
	};

	return (
		<Navbar variant="dark" expand="lg" className="px-3 navbar-main">
			<Navbar.Toggle aria-controls="navbar-nav" />
			<Navbar.Collapse id="navbar-nav">
				<Nav className="me-auto">
					<DarkDropdown
						items={projectNames}
						keys={projectKeys}
						defaultText={getDefaultProjectName()}
						headerText="Select Project"
						onItemSelect={handleProjectChange}
					/>
					<DarkDropdown
						items={envItems}
						keys={envKeys}
						defaultText={selectedEnvName}
						headerText="Select Environment"
						onItemSelect={handleEnvChange}
					/>
				</Nav>
				<Nav className="ms-auto">
					{/* <Button variant="dark" className="px-3 me-4 text-white">
						<i className="bi bi-play-fill me-2"></i>
						Run
					</Button> */}
					<Button variant="dark" className="px-3 text-white" onClick={handleOpenModal}>
						<i className="bi bi-cloud-arrow-up-fill me-2"></i>
						Deploy
					</Button>
				</Nav>
			</Navbar.Collapse>

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
