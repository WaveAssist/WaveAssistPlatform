import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import Spinner from "react-bootstrap/Spinner";
import "./deploy_component.css";
import GreenLogo from "../assets/Logo/GreenLogo_Full_white_no_w.png";
import { fetchAllProjectsAPI } from "../services/all_projects_services";

const DeployComponent: React.FC = () => {
	const [searchParams] = useSearchParams();
	const navigate = useNavigate();
	const [isDeploying, setIsDeploying] = useState(false);
	const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
	const [githubRepo, setGithubRepo] = useState<string>("");

	const deploymentMessages = [
		"🚀 Initializing your AI assistant... ",
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
			}, 2000);
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
		// Always deploy when github repo is available
		if (githubRepo && !isDeploying) {
			handleDeploy();
		}
	}, [githubRepo, isDeploying]); // Depend on githubRepo to trigger after update

	const fetchTemplate = async (templateKey: string) => {
		try {
			const res = await axios.get(`https://api.waveassist.io/fetch_assistant/${templateKey}/`);
			if (res.data.success === "1") {
				setGithubRepo(res.data.data.github_url);
			} else {
				throw new Error("Failed to fetch assistant with new endpoint");
			}
		} catch (err) {
			console.error("Error fetching assistant:", err);
			const currentParams = new URLSearchParams(searchParams);
			navigate(`/manage?${currentParams.toString()}`);
		}
	};

	useEffect(() => {
		const uid = localStorage.getItem("uid");
		const templateKey = searchParams.get("template_key");
		console.log("searchParams", searchParams);

		if (!templateKey) {
			alert("Missing template_key in URL.");
			const currentParams = new URLSearchParams(searchParams);
			navigate(`/manage?${currentParams.toString()}`);
			return;
		}

		if (!uid) {
			// Preserve all URL parameters when redirecting to login
			const currentParams = new URLSearchParams(searchParams);
			const redirectUrl = `/deploy?${currentParams.toString()}`;
			localStorage.setItem("postLoginRedirect", redirectUrl);
			navigate(`/login?${currentParams.toString()}`);
			return;
		}

		fetchTemplate(templateKey);
	}, [searchParams, navigate]);

	const handleDeploy = async () => {
		const uid = localStorage.getItem("uid");
		if (!uid || !githubRepo) return;
		setIsDeploying(true);
		try {
			const formData = new FormData();
			formData.append("repo_url", githubRepo);
			formData.append("template_key", searchParams.get("template_key") || "");
			formData.append("uid", uid);
			formData.append("timezone", Intl.DateTimeFormat().resolvedOptions().timeZone);
			const isPremium = searchParams.get("is_premium") === "true";
			formData.append("is_premium", isPremium ? "1" : "0");
			const response = await axios.post("https://api.waveassist.io/template/deploy_template/", formData, {
				headers: { "Content-Type": "multipart/form-data" },
			});
			if (response.data.success === "1") {
				localStorage.setItem("is_template_run", "true");
				// The project key might be in a different field in the response
				const projectKey = response.data.data?.project_key || response.data.project_key;
				if (projectKey) {
					localStorage.setItem("selected_project_key", projectKey);
					localStorage.setItem("selected_env_key", projectKey + "_default");
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
				// Navigate to the project after successful deployment
				navigate(`/manage/assistant?project_key=${projectKey}`, {
					state: { openWizard: true, allowDismiss: false },
				});
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

	return (
		<div className="deploy-loading-page">
			<div className="deploy-loading-container">
				<div className="text-center">
					<img src={GreenLogo} alt="WaveAssist Logo" className="deploy-logo mb-4" />
					<div className="deploy-loader">
						<Spinner animation="border" role="status" variant="success" className="mb-3" />
						{isDeploying && <p className="deploy-message">{deploymentMessages[currentMessageIndex]}</p>}
						{!isDeploying && <p className="deploy-message">Preparing your assistant...</p>}
					</div>
				</div>
			</div>
		</div>
	);
};

export default DeployComponent;
