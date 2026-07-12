import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import Spinner from "react-bootstrap/Spinner";
import "./deploy_component.css";
import { BrandLogo, getBrand } from "../config/branding";
import { fetchAllProjectsAPI } from "../services/all_projects_services";
import { BASE_URL } from "../services/base_service";

const DeployComponent: React.FC = () => {
	const [searchParams] = useSearchParams();
	const navigate = useNavigate();
	const brand = getBrand();
	const [isDeploying, setIsDeploying] = useState(false);
	const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
	const [githubRepo, setGithubRepo] = useState<string>("");
	// Existing projects for this template: null = not checked yet, [] = none. When one already
	// exists we ask before creating another instead of auto-deploying, so a stray visit to /deploy
	// (e.g. a returning user clicking a marketing link) can't silently spin up duplicate projects.
	const [existingMatches, setExistingMatches] = useState<any[] | null>(null);
	const [forceCreate, setForceCreate] = useState(false);

	const deploymentMessages = [
		"Setting things up...",
		"Preparing your account...",
		"Configuring your workspace...",
		"Bringing everything online...",
		"Almost ready...",
	];

	const hasExisting = existingMatches !== null && existingMatches.length > 0;
	const showConfirm = hasExisting && !forceCreate && !isDeploying;

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

	// Auto-deploy once the template repo is known AND we've resolved existing projects. If the user
	// already has a project for this template we hold and show the confirm screen instead; deploying
	// only proceeds for a first project or an explicit "Create another".
	useEffect(() => {
		if (!githubRepo || isDeploying) return;
		if (existingMatches === null) return; // still checking
		if (existingMatches.length > 0 && !forceCreate) return; // waiting on the confirm screen
		handleDeploy();
	}, [githubRepo, isDeploying, existingMatches, forceCreate]);

	const fetchTemplate = async (templateKey: string) => {
		try {
			const res = await axios.get(`${BASE_URL}/fetch_assistant/${templateKey}/`);
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

	// Look up whether the user already has a project for this template, matched the same way the
	// projects list does (exact template_key, or a project_key that contains it).
	const checkExisting = async (templateKey: string) => {
		try {
			const projectData = await fetchAllProjectsAPI();
			const matches = (projectData.project_array || []).filter(
				(p: any) => p.template_key === templateKey || (p.project_key || "").toLowerCase().includes(templateKey)
			);
			setExistingMatches(matches);
		} catch (err) {
			// Fail open: if we can't read the list, don't block a genuine first deploy.
			console.error("Failed to check existing projects:", err);
			setExistingMatches([]);
		}
	};

	useEffect(() => {
		const uid = localStorage.getItem("uid");
		// In a scoped brand (e.g. gitzoid), a bare /deploy defaults to that brand's template.
		const templateKey = searchParams.get("template_key") || (brand.scoped ? brand.templateKey : null);

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
		checkExisting(templateKey);
	}, [searchParams, navigate]);

	const handleDeploy = async () => {
		const uid = localStorage.getItem("uid");
		if (!uid || !githubRepo) return;
		setIsDeploying(true);
		try {
			const formData = new FormData();
			formData.append("repo_url", githubRepo);
			formData.append("template_key", searchParams.get("template_key") || (brand.scoped ? brand.templateKey || "" : ""));
			formData.append("uid", uid);
			formData.append("timezone", Intl.DateTimeFormat().resolvedOptions().timeZone);
			const isPremium = searchParams.get("is_premium") === "true";
			formData.append("is_premium", isPremium ? "1" : "0");
			const response = await axios.post(`${BASE_URL}/template/deploy_template/`, formData, {
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
				alert("Failed to deploy project, please try again.");
			}
		} catch (error) {
			console.error("Deploy failed:", error);
			alert("Something went wrong while deploying. Please try again.");
		} finally {
			setIsDeploying(false);
		}
	};

	const handleOpenExisting = () => {
		const matches = existingMatches || [];
		if (matches.length === 1) {
			navigate(`/manage/assistant?project_key=${matches[0].project_key}`);
		} else {
			navigate(`/manage`);
		}
	};

	// Already have a project for this template: confirm before creating another.
	if (showConfirm) {
		return (
			<div className="deploy-loading-page">
				<div className="deploy-loading-container">
					<div className="text-center" style={{ maxWidth: 360, margin: "0 auto" }}>
						<BrandLogo className="deploy-logo mb-4" size={34} />
						<h5 style={{ color: "var(--color-text-primary)", fontWeight: 600, marginBottom: 10 }}>
							Create another {brand.title} project?
						</h5>
						<p style={{ color: "var(--color-text-secondary)", fontSize: 13.5, lineHeight: 1.5, marginBottom: 24 }}>
							You already have a {brand.title} project. Open the one you have, or spin up a new one.
						</p>
						<button
							onClick={handleOpenExisting}
							style={{
								width: "100%",
								padding: "10px 16px",
								borderRadius: 8,
								border: "none",
								background: "var(--color-primary)",
								color: "var(--color-text-button)",
								fontWeight: 600,
								fontSize: 14,
								cursor: "pointer",
								marginBottom: 10,
							}}>
							Open my {brand.title}
						</button>
						<button
							onClick={() => setForceCreate(true)}
							style={{
								width: "100%",
								padding: "10px 16px",
								borderRadius: 8,
								background: "transparent",
								border: "1px solid var(--color-border)",
								color: "var(--color-text-secondary)",
								fontWeight: 500,
								fontSize: 14,
								cursor: "pointer",
							}}>
							Create another
						</button>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="deploy-loading-page">
			<div className="deploy-loading-container">
				<div className="text-center">
					<BrandLogo className="deploy-logo mb-4" size={34} />
					<div className="deploy-loader">
						<Spinner animation="border" role="status" variant="success" className="mb-3" />
						{isDeploying && <p className="deploy-message">{deploymentMessages[currentMessageIndex]}</p>}
						{!isDeploying && <p className="deploy-message">Getting things ready...</p>}
					</div>
				</div>
			</div>
		</div>
	);
};

export default DeployComponent;
