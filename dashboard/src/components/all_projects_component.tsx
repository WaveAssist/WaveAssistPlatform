import React, { useEffect, useState } from "react";
import Joyride, { Step } from "react-joyride";

import Button from "react-bootstrap/Button";
import Modal from "react-bootstrap/Modal";
import Spinner from "react-bootstrap/Spinner";
import Alert from "react-bootstrap/Alert";
import GreenLogo from "../assets/Logo/GreenLogo_Full_white_no_w.png";

import { useNavigate } from "react-router-dom";
import { fetchAllProjectsAPI, createProjectAPI, deleteProjectApi } from "../services/all_projects_services";
import { useToast } from "../utils/toast_context";
import "./all_projects_component.css";

import { usePostHog } from "posthog-js/react";

interface Project {
	project_key: string;
	name: string;
	is_premium?: boolean;
	// Add other project properties as needed
}

const AllProjectsComponent: React.FC = () => {
	const [newProjectName, setNewProjectName] = useState("");
	const [newProjectKey, setNewProjectKey] = useState("");
	const [showAlert, setShowAlert] = useState(false);
	const [projectArray, setProjectArray] = useState<Project[]>([]);
	const [isUserPremium, setIsUserPremium] = useState(false);
	const [showModal, setShowModal] = useState(false);
	const [isProjectKeyEdited, setIsProjectKeyEdited] = useState(false);
	const [loading, setLoading] = useState(true);
	const navigate = useNavigate();
	const { showToast } = useToast();
	const posthog = usePostHog();

	const [runTour, setRunTour] = useState(false);
	const steps: Step[] = [
		{
			target: ".add-project-card",
			content: "Create a new project from scratch.",
			disableBeacon: true,
		},
		{
			target: ".use-template-button",
			content: "Or start quickly with a assistant template.",
			disableBeacon: true,
			locale: { last: "Ok" },
		},
	];

	useEffect(() => {
		fetchData();
		// Get user's premium status from localStorage
		const userData = JSON.parse(localStorage.getItem("user_data") || "{}");
		const premiumLocal = localStorage.getItem("is_premium") === "true";
		setIsUserPremium(premiumLocal || Boolean(userData.is_premium));
	}, []);

	useEffect(() => {
		if (!isProjectKeyEdited) {
			const generatedKey = newProjectName.toLowerCase().replace(/\s+/g, "_");
			setNewProjectKey(generatedKey);
		}
	}, [newProjectName]);

	const fetchData = async () => {
		setLoading(true);
		try {
			const data = await fetchAllProjectsAPI();
			setProjectArray(data.project_array);

			// Store the premium status of all projects in localStorage
			if (data.project_array && data.project_array.length > 0) {
				// Get the currently selected project key
				const selectedProjectKey = localStorage.getItem("selected_project_key");

				// Find the selected project in the project array
				const selectedProject = data.project_array.find((project: any) => project.project_key === selectedProjectKey);

				// If a project is selected, store its premium status in localStorage
				if (selectedProject) {
					localStorage.setItem("is_project_premium", selectedProject.is_premium ? "true" : "false");
				}
			}

			if (data.project_array.length === 0) {
				const tourCompleted = localStorage.getItem("create_project_tour_completed");
				if (tourCompleted == null) {
					setRunTour(true);
					localStorage.setItem("create_project_tour_completed", "true");
					localStorage.setItem("is_new_user", "true");
				}
			}
			localStorage.setItem("projects_array", JSON.stringify(data.project_array));
		} catch (error) {
			console.error("FetchAllProjects failed:", error);
			showToast("Something went wrong with loading projects, please try again.", "danger");
		} finally {
			setLoading(false);
		}
	};

	const handleLogout = async () => {
		try {
			// Add your sign-out logic here
			localStorage.removeItem("uid");
			localStorage.removeItem("projects_array");
			localStorage.removeItem("selected_project_key");
			localStorage.removeItem("user_data");
			navigate("/login");
		} catch (error) {
			console.error("Error logging out:", error);
		}
	};

	const handleCloseModal = () => {
		setShowModal(false);
	};

	const handleDeleteProject = async (projectKey: string) => {
		//Show bootstrap alert to ask for confirmation
		const confirmDelete = window.confirm(
			"Are you sure you want to delete this project? This action cannot be undone and will also delete all associated nodes and data. Do you want to proceed?"
		);
		if (!confirmDelete) {
			return;
		}

		try {
			await deleteProjectApi(projectKey);
			showToast("Project deleted successfully", "success");
			fetchData();
		} catch (error) {
			console.error("Project Deletetion Failed:", error);
			var error_message = "Something went wrong deleting the project: " + error;
			showToast(error_message, "danger");
		}
	};

	const handleCreateProject = async () => {
		try {
			await createProjectAPI(newProjectName, newProjectKey);
			showToast("Project created successfully", "success");
			setShowAlert(false);
			handleCloseModal();

			// Update projects array in localStorage
			const existingProjects = JSON.parse(localStorage.getItem("projects_array") || "[]");
			const newProject: Project = {
				name: newProjectName,
				project_key: newProjectKey,
				is_premium: false, // New projects are not premium by default
			};
			existingProjects.push(newProject);
			localStorage.setItem("projects_array", JSON.stringify(existingProjects));

			// Set selected project and premium status, then navigate
			localStorage.setItem("selected_project_key", newProjectKey);
			localStorage.setItem("selected_env_key", newProjectKey + "_default");
			localStorage.setItem("is_project_premium", "false");

			// Check user's plan to determine navigation destination
			const planName = localStorage.getItem("plan_name");
			const destination = planName === "operator" ? "runs" : "nodes";
			navigate(`/manage/${destination}?project_key=${newProjectKey}`);
		} catch (error) {
			console.error("FetchAllProjects failed:", error);
			var error_message = "Something went wrong creating the project: " + error;
			showToast(error_message, "danger");
		}
	};

	const handleViewDetails = (projectKey: string) => {
		// Find the selected project in the project array
		const selectedProject = projectArray.find((p: Project) => p.project_key === projectKey);

		// Store the project key and premium status in localStorage
		localStorage.setItem("selected_project_key", projectKey);
		localStorage.setItem("selected_env_key", projectKey + "_default");
		if (selectedProject) {
			localStorage.setItem("is_project_premium", selectedProject.is_premium ? "true" : "false");
			localStorage.setItem("selected_project", JSON.stringify(selectedProject)); // <-- Ensure this is set
		}

		// Track project viewed and contextual pageview
		try {
			posthog?.capture("project_viewed", {
				project_id: projectKey,
				page_category: "project_detail",
			});
			posthog?.capture("$pageview", {
				page_category: "project_detail",
				project_id: projectKey,
				environment: localStorage.getItem("selected_env_key") || undefined,
			});
		} catch (_err) {}

		navigate(`/manage/assistant?project_key=${projectKey}`);
	};

	return (
		<div className="base_component">
			<div className="dashboard-header row flex-md-nowrap py-3 px-3">
				<div className="col-6 d-flex align-items-center justify-content-start">
					<div className="d-flex align-items-center mt-2" style={{ height: "100%" }}>
						<img src={GreenLogo} className="wp_logo" alt="WavePredict Logo" />
					</div>
				</div>
				<div className="col-6 d-flex flex-row flex-nowrap justify-content-end align-items-center button-row">
					<a
						href="https://waveassist.io/assistants"
						target="_self"
						rel="noopener noreferrer"
						className="btn btn-outline-secondary btn-sm ms-2 use-template-button">
						<i className="bi bi-copy"></i>
						<span className="d-none d-md-inline ms-1">Assistants</span>
					</a>
					<a href="https://docs.waveassist.io" target="_blank" rel="noopener noreferrer" className="btn btn-outline-secondary btn-sm ms-2">
						<i className="bi bi-journal-text"></i>
						<span className="d-none d-md-inline ms-1">Docs</span>
					</a>
					<button className="btn btn-outline-secondary btn-sm logout_button ms-2 me-2" onClick={handleLogout}>
						<i className="bi bi-box-arrow-right"></i>
						<span className="d-none d-md-inline ms-1">Logout</span>
					</button>
				</div>
			</div>
			{loading && (
				<div className="d-flex justify-content-center align-items-center" style={{ minHeight: "400px" }}>
					<Spinner animation="border" role="status" variant="success">
						<span className="visually-hidden">Loading...</span>
					</Spinner>
				</div>
			)}
			{!loading && (
				<div className="admin-panel">
					<div className="content projects-row">
						<div className="header">
							<h2 className="admin-title mb-3 translucent_white">All Assistants</h2>
						</div>

						<div className="row ">
							<div className="col-sm-4 project-card  " onClick={() => window.open("https://waveassist.io/assistants", "_self")}>
								<div className="card text-white bg-dark mb-3 ml-5 mr-5 add-project-card">
									<div className="card-body d-flex align-items-center justify-content-center">
										<div className="text-center">
											<i className="bi bi-plus-lg add-icon translucent_blue fs-3"></i>
											<p className="add-text translucent_blue">Add Assistant</p>
										</div>
									</div>
								</div>
							</div>
							{projectArray.map((project: any) => (
								<div className="col-sm-4 project-card ml-5" key={project.project_key} onClick={() => handleViewDetails(project.project_key)}>
									<div className="card text-white bg-dark mb-3 ml-5 mr-5">
										<div className="card-body position-relative p-3">
											<div className="d-flex align-items-center">
												<h5 className="card-title translucent_white fs-4 mb-0">{project.name}</h5>
												{project.is_premium && (
													<span className="badge bg-warning text-dark ms-2" style={{ fontSize: "0.6rem" }}>
														PREMIUM
													</span>
												)}
											</div>
											<h5 className="card-title translucent_white_more fs-6 mb-3">{project.project_key}</h5>
											<button
												className="btn btn-dark delete-icon translucent_white p-2"
												onClick={(e) => {
													e.stopPropagation();
													handleDeleteProject(project.project_key);
												}}
												title={project.is_premium && !isUserPremium ? "Premium projects cannot be deleted" : ""}>
												<i className="bi bi-trash-fill"></i>
											</button>
										</div>
									</div>
								</div>
							))}
						</div>
					</div>
				</div>
			)}

			<Modal show={showModal} onHide={handleCloseModal}>
				<Modal.Header closeButton>
					<Modal.Title className="modal-title">Add New Project</Modal.Title>
				</Modal.Header>

				<Modal.Body>
					<div className="mb-3">
						<label htmlFor="projectNameInput" className="form-label">
							Project Name
						</label>
						<input
							type="text"
							className="form-control"
							id="projectNameInput"
							value={newProjectName}
							onChange={(e) => setNewProjectName(e.target.value)}
						/>

						<hr></hr>
						<label htmlFor="projectNameInput" className="form-label">
							Project Key
						</label>
						<input
							type="text"
							className="form-control"
							id="projectKeyInput"
							value={newProjectKey}
							onChange={(e) => {
								setNewProjectKey(e.target.value);
								setIsProjectKeyEdited(true); // prevent auto-sync from this point
							}}
						/>
						<div id="projectNameHelp" className="form-text" style={{ color: "rgba(255, 255, 255, 0.6)", fontSize: "0.9rem" }}>
							Must be lowercase and without spaces.
						</div>

						{showAlert && <Alert variant="danger">Could not create the project, try a different name.</Alert>}
					</div>
				</Modal.Body>
				<Modal.Footer className="d-flex justify-content-between align-items-center">
					<div className="text-white small mt-2">
						<div>Want a head start?</div>
						<Button
							size="sm"
							className="p-0 translucent_blue bg-transparent border-0 text-decoration-none"
							onClick={() => window.open("https://waveassist.io/assistants", "_self")}
							onMouseOver={(e) => e.currentTarget.classList.add("text-decoration-underline")}
							onMouseOut={(e) => e.currentTarget.classList.remove("text-decoration-underline")}>
							{/* <i className="bi bi-lightning-fill me-1" style={{ fontSize: "0.8rem" }}></i> */}
							Use an assistant instead →
						</Button>
					</div>

					<div className="mt-2">
						<Button variant="secondary" onClick={handleCloseModal}>
							Close
						</Button>
						<Button variant="primary" onClick={handleCreateProject} className="ms-2">
							Create
						</Button>
					</div>
				</Modal.Footer>
			</Modal>
			<Joyride
				steps={steps}
				run={runTour}
				continuous={true}
				showSkipButton={true}
				showProgress={true}
				disableCloseOnEsc={true}
				disableOverlayClose={true}
				floaterProps={{ disableAnimation: true }}
				callback={(data) => {
					if (data.status === "finished" || data.status === "skipped") {
						setRunTour(false);
					}
				}}
				styles={{
					options: {
						arrowColor: "#0D1B2A", // blue-black background
						backgroundColor: "#0D1B2A",
						primaryColor: "#1ED66C", // brand green button
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
						backgroundColor: "#1ED66C", // brand green
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
			/>
		</div>
	);
};

export default AllProjectsComponent;
