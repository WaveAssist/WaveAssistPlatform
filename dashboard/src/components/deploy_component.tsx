import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import Modal from "react-bootstrap/Modal";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import ReactMarkdown from "react-markdown";
import "./deploy_component.css";
import GreenLogo from "../assets/Logo/GreenLogo_Full_white_no_w.png";

const DeployComponent: React.FC = () => {
	const [searchParams] = useSearchParams();
	const navigate = useNavigate();
	const [templateData, setTemplateData] = useState<any>(null);
	const [isDeploying, setIsDeploying] = useState(false);
	const [showSuccessModal, setShowSuccessModal] = useState(false);

	useEffect(() => {
		const uid = localStorage.getItem("uid");
		const templateKey = searchParams.get("template_key");

		if (!templateKey) {
			alert("Missing template_key in URL.");
			navigate("/manage");
			return;
		}

		if (!uid) {
			const redirectUrl = `/deploy?template_key=${templateKey}`;
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
					alert("Failed to fetch template.");
					navigate("/manage");
				}
			} catch (err) {
				console.error("Error fetching template:", err);
				alert("Could not fetch template data.");
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
			formData.append("uid", uid);
			const response = await axios.post("https://api.waveassist.io/template/deploy_template/", formData, {
				headers: { "Content-Type": "multipart/form-data" },
			});
			if (response.data.success === "1") {
				setShowSuccessModal(true);
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
			localStorage.removeItem("project_array");
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
							<Button variant="success" className="w-100 mb-2 fw-semibold py-2" onClick={handleDeploy} disabled={isDeploying}>
								🚀 Deploy Now
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
							<div className="mb-3 pb-3">
								{templateData.tags?.map((tag: string, idx: number) => (
									<span key={idx} className="badge bg-secondary me-2 rounded-pill px-3 py-2">
										{tag}
									</span>
								))}
							</div>
							<Button variant="success" className="w-100 mb-2 fw-semibold py-2" onClick={handleDeploy} disabled={isDeploying}>
								🚀 Deploy Now
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
			<Modal show={isDeploying} centered backdrop="static" keyboard={false}>
				<Modal.Body className="text-center py-5">
					<Spinner animation="border" role="status" className="mb-3" />
					<h5>Deploying your template, this may take a minute...</h5>
				</Modal.Body>
			</Modal>
			<Modal show={showSuccessModal} backdrop="static" keyboard={false} centered>
				<Modal.Header>
					<Modal.Title>✅ Deployment Successful</Modal.Title>
				</Modal.Header>
				<Modal.Body className="text-center">
					<p className="pt-4">All set! Your project is ready to use.</p>
					<Button variant="success" className="mt-3 px-4 py-2 fw-semibold" onClick={() => navigate("/manage")}>
						Go to Dashboard
					</Button>
				</Modal.Body>
			</Modal>
		</div>
	);
};

export default DeployComponent;
