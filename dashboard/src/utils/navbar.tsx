import React, { useEffect, useState } from "react";
import { Navbar, Nav, Button } from "react-bootstrap";
import "./navbar.css";
import DarkDropdown from "./dark_dropdown";
import { fetchEnvironmentsApi } from "../services/navbar_services";
import { useToast } from "./toast_context";

const NavbarComponent: React.FC = () => {
	const { showToast } = useToast();

	const [environmentArray, setEnvironmentArray] = useState<{ name: string; key: string }[]>([]);
	const envItems = environmentArray.map((env) => env.name);
	const envKeys = environmentArray.map((env) => env.key);

	const selectedProjectKey = localStorage.getItem("selected_project_key");
	const projectsArray = JSON.parse(localStorage.getItem("projects_array") || "[]");
	const projectKeys = projectsArray.map((project: any) => project.project_key);
	const projectNames = projectsArray.map((project: any) => project.name + " - " + project.project_key);
	const [selectedEnvName, setSelectedEnvName] = useState("Default");

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

	const handleProjectChange = (_project_name: string, project_key: string) => {
		localStorage.setItem("selected_project_key", project_key);
		fetchEnvironments();
	};

	const handleEnvChange = (env_name: string, env_key: string) => {
		localStorage.setItem("selected_env_key", env_key);
		setSelectedEnvName(env_name);
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
					<Button variant="dark" className="px-3 me-4 text-white">
						<i className="bi bi-play-fill me-2"></i>
						Run
					</Button>
					<Button variant="dark" className="px-3 text-white">
						<i className="bi bi-cloud-arrow-up-fill me-2"></i>
						Deploy
					</Button>
				</Nav>
			</Navbar.Collapse>
		</Navbar>
	);
};

export default NavbarComponent;
