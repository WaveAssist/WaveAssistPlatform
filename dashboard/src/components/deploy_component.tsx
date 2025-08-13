import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import Modal from "react-bootstrap/Modal";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import ReactMarkdown from "react-markdown";
import "./deploy_component.css";
import GreenLogo from "../assets/Logo/GreenLogo_Full_white_no_w.png";
import { fetchAllProjectsAPI } from "../services/all_projects_services";

const DeployComponent: React.FC = () => {
	const [searchParams] = useSearchParams();
	const navigate = useNavigate();
	const [templateData, setTemplateData] = useState<any>(null);
	const [isDeploying, setIsDeploying] = useState(false);
	const [showSuccessModal, setShowSuccessModal] = useState(false);
	const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
	const [hasAutoDeployed, setHasAutoDeployed] = useState(false); // New flag to prevent re-triggers

	const deploymentMessages = [
		"🚀 Initializing your AI assistant, this may take a minute.. ",
		"🚀 Initializing your AI assistant, this may take a minute..",
		"📦 Installing dependencies to power your workflow...",
		"🔧 Configuring settings for peak performance...",
		"⚡ Activating your customized assistant...",
		"✨ Almost ready! Polishing the final touches...",
	];

	// Rotate messages every 2 seconds when deploying
	useEffect(() => {
		let interval: NodeJS.Timeout;
		if (isDeploying) {
			interval = setInterval(() => {
				setCurrentMessageIndex((prevIndex) => (prevIndex < deploymentMessages.length - 1 ? prevIndex + 1 : prevIndex));
			}, 3000);
		} else {
			setCurrentMessageIndex(0);
		}

		return () => {
			if (interval) {
				clearInterval(interval);
			}
		};
	}, [isDeploying]);

	useEffect(() => {
		const autoDeploy = searchParams.get("auto_deploy") === "true";
		if (templateData && autoDeploy && !hasAutoDeployed) {
			setHasAutoDeployed(true); // Mark as triggered to avoid repeats
			handleDeploy();
		}
	}, [templateData, searchParams]); // Depend on templateData to trigger after update

	useEffect(() => {
		const uid = localStorage.getItem("uid");
		const templateKey = searchParams.get("template_key");
		const autoDeploy = searchParams.get("auto_deploy") === "true";
		console.log("searchParams", searchParams);
		console.log("autoDeploy", autoDeploy);

		if (!templateKey) {
			alert("Missing template_key in URL.");
			navigate("/manage");
			return;
		}

		if (!uid) {
			// Preserve all URL parameters when redirecting to login
			const currentParams = new URLSearchParams(searchParams);
			const redirectUrl = `/deploy?${currentParams.toString()}`;
			localStorage.setItem("postLoginRedirect", redirectUrl);
			navigate(`/login`);
			return;
		}

		const fetchTemplate = async () => {
			try {
				const res = await axios.get(`https://api.waveassist.io/templates/${templateKey}/`);
				if (res.data.success === "1") {
					setTemplateData(res.data.data);
				} else {
					alert("Failed to fetch assistant.");
					navigate("/manage");
				}
			} catch (err) {
				console.error("Error fetching assistant:", err);
				alert("Could not fetch assistant data.");
				navigate("/manage");
			}
		};
		fetchTemplate();
	}, [searchParams, navigate]);

	const handleDeploy = async () => {
		const uid = localStorage.getItem("uid");
		if (!uid || !templateData?.repo_url) return;
		setIsDeploying(true);
		try {
			const formData = new FormData();
			formData.append("repo_url", templateData.repo_url);
			formData.append("template_key", searchParams.get("template_key") || "");
			formData.append("uid", uid);
			formData.append("timezone", Intl.DateTimeFormat().resolvedOptions().timeZone);
			const isPremium = searchParams.get("is_premium") === "true";
			formData.append("is_premium", isPremium ? "1" : "0");
			const response = await axios.post("https://api.waveassist.io/template/deploy_template/", formData, {
				headers: { "Content-Type": "multipart/form-data" },
			});
			if (response.data.success === "1") {
				setShowSuccessModal(true);
				localStorage.setItem("is_template_run", "true");
				// The project key might be in a different field in the response
				const projectKey = response.data.data?.project_key || response.data.project_key;
				if (projectKey) {
					localStorage.setItem("selected_project_key", projectKey);
					try {
						const projectData = await fetchAllProjectsAPI();
						localStorage.setItem("projects_array", JSON.stringify(projectData.project_array));
						const selectedProject = projectData.project_array.find((p: any) => p.project_key === projectKey);
						if (selectedProject) {
							localStorage.setItem("selected_project", JSON.stringify(selectedProject));
						}
					} catch (err) {
						console.error("Failed to refresh projects:", err);
					}
				} else {
					console.error("No project key found in response");
				}
			} else {
				alert("❌ Failed to deploy project, please try again.");
			}
		} catch (error) {
			console.error("Deploy failed:", error);
			alert("❌ Something went wrong while deploying. Please try again.");
		} finally {
			setIsDeploying(false);
		}
	};

	if (!templateData) return null;

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

	return (
		<div className="deploy-container">
			<div className="dashboard-header row align-items-center">
				<div className="col-12 col-md-8  mb-md-0 d-flex justify-content-center justify-content-md-start">
					<img src={GreenLogo} className="wp_logo" alt="WavePredict Logo" />
				</div>
				<div className="col-12 col-md-4 mb-3 d-flex justify-content-center justify-content-md-end">
					<button className="btn btn-outline-secondary logout_button" onClick={handleLogout}>
						Logout
					</button>
				</div>
			</div>

			<div className="separator"></div>

			<div className="row w-100">
				<div className="col-lg-8 order-2 order-lg-1">
					<div className="deploy-card">
						<div className="deploy-content">
							<h1>{templateData.title}</h1>
							<p className="description">{templateData.description}</p>
							<div className="mb-3 pb-3">
								{templateData.tags?.map((tag: string, idx: number) => (
									<span key={idx} className="badge bg-secondary me-2 rounded-pill px-3 py-2">
										{tag}
									</span>
								))}
							</div>
							<div className="markdown-body mb-4 mt-4">
								<ReactMarkdown>{templateData.markdown}</ReactMarkdown>
							</div>
							<Button variant="success" className="w-100 mb-2 py-2" onClick={handleDeploy} disabled={isDeploying}>
								{isDeploying ? "Deploying..." : "Deploy Now"}
							</Button>
						</div>
					</div>
				</div>

				<div className="col-lg-4 order-1 order-lg-2">
					<div className="deploy-card text-center">
						<div className="deploy-image">
							<img src={templateData.thumbnail} alt={templateData.title} />
						</div>
						<div className="deploy-content">
							<h4>{templateData.title}</h4>
							<p className="description">{templateData.description}</p>

							<Button variant="success" className="w-100 mb-2 mt-4 py-2" onClick={handleDeploy} disabled={isDeploying}>
								{isDeploying ? "Deploying..." : "Deploy Now"}
							</Button>
						</div>
					</div>
				</div>
			</div>

			<div className="text-center mt-4">
				<Button variant="outline-light" onClick={() => navigate("/manage")}>
					← Go to all projects
				</Button>
			</div>
			<Modal show={isDeploying} centered backdrop="static" keyboard={false} dialogClassName="deploy-modal">
				<Modal.Body className="text-center py-5">
					<Spinner animation="border" role="status" className="mb-3" />
					<h5>{deploymentMessages[currentMessageIndex]}</h5>
				</Modal.Body>
			</Modal>
			<Modal show={showSuccessModal} backdrop="static" keyboard={false} centered dialogClassName="deploy-modal">
				<Modal.Header>
					<Modal.Title>✅ Deployment Successful</Modal.Title>
				</Modal.Header>
				<Modal.Body className="text-center">
					<p className="pt-4">All set! Your project is ready to use.</p>
					<Button
						variant="success"
						className="mt-3 px-4 py-2 fw-semibold"
						onClick={() => {
							navigate(`/manage/nodes?project_key=${localStorage.getItem("selected_project_key")}`, {
								state: { openWizard: true, allowDismiss: false },
							});
						}}>
						Go to Assistant
					</Button>
				</Modal.Body>
			</Modal>
		</div>
	);
};

export default DeployComponent;
