// src/Sidebar.js
import { Link, useLocation, useNavigate } from "react-router-dom";
import "./sidebar.css";
import GreenLogo from "../assets/Logo/GreenLogo_Full_white_no_w.png";
import { useState } from "react";
import Joyride, { Step } from "react-joyride";

const Sidebar = () => {
	const location = useLocation();
	const navigate = useNavigate();
	const [runTour, setRunTour] = useState(true);

	const steps: Step[] = [
		{
			target: ".packages-link",
			content: "Click here to manage your installed packages.",
		},
		{
			target: ".logs-link",
			content: "Here you can view logs of executed workflows.",
		},
		{
			target: ".keys-link",
			content: "Click here to download your API keys.",
		},
	];

	const handleLogout = () => {
		localStorage.removeItem("uid");
		localStorage.removeItem("project_array");
		localStorage.removeItem("selected_project_key");
		localStorage.removeItem("user_data");
		navigate("/login");
	};

	const handleDownloadKeys = () => {
		const userData = localStorage.getItem("user_data");
		if (!userData) {
			alert("No user data found.");
			return;
		}

		const parsedData = JSON.parse(userData);
		const excludeKeys = ["name", "can_create_projects", "id"];
		const filteredEntries = Object.entries(parsedData).filter(([key]) => !excludeKeys.includes(key));

		if (filteredEntries.length === 0) {
			alert("No keys to download.");
			return;
		}

		const csvContent =
			"data:text/csv;charset=utf-8," +
			filteredEntries.map(([key, value]) => `${key},${value}`).join("\n");

		const encodedUri = encodeURI(csvContent);
		const link = document.createElement("a");
		link.setAttribute("href", encodedUri);
		link.setAttribute("download", "waveassist_keys.csv");
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
	};

	return (
		<div className="side-div d-flex flex-column flex-shrink-0 p-3 vh-100">
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
					if (data.status === "finished" || data.status === "skipped") {
						setRunTour(false);
					}
				}}
			/>

			<div className="d-flex flex-column align-items-center mb-4 me-md-auto text-white text-decoration-none w-100">
				<a href="/">
					<img src={GreenLogo} className="wp_logo" alt="WavePredict Logo" />
				</a>
			</div>

			<ul className="nav nav-pills flex-column mb-4">
				<li className="nav-item">
					<Link
						to="/manage/nodes"
						className={`nav-link ${location.pathname === "/manage/nodes" ? "active" : "text-white"} mb-1`}
					>
						<i className="bi bi-bezier2 me-2"></i>
						Nodes
					</Link>
				</li>
				<li className="nav-item">
					<Link
						to="/manage/variables"
						className={`nav-link ${location.pathname === "/manage/variables" ? "active" : "text-white"} mb-1`}
					>
						<i className="bi bi-table me-2"></i>
						Variables
					</Link>
				</li>
				<li className="nav-item">
					<Link
						to="/manage/packages"
						className={`nav-link ${location.pathname === "/manage/packages" ? "active" : "text-white"} mb-1 packages-link`}
					>
						<i className="bi bi-box-fill me-2"></i>
						Packages
					</Link>
				</li>
				<li className="nav-item">
					<Link
						to="/manage/deployments"
						className={`nav-link ${location.pathname === "/manage/deployments" ? "active" : "text-white"} mb-1`}
					>
						<i className="bi bi-cloud-arrow-up-fill me-2"></i>
						Deployments
					</Link>
				</li>
				<li className="nav-item">
					<Link
						to="/manage/environments"
						className={`nav-link ${location.pathname === "/manage/environments" ? "active" : "text-white"} mb-1`}
					>
						<i className="bi bi-stack me-2"></i>
						Environments
					</Link>
				</li>
				<li className="nav-item">
					<Link
						to="/manage/logs"
						className={`nav-link ${location.pathname === "/manage/logs" ? "active" : "text-white"} mb-1 logs-link`}
					>
						<i className="bi bi-file-text-fill me-2"></i>
						Logs
					</Link>
				</li>
			</ul>

			<div className="mt-auto">
				<hr className="text-white" />
				<div className="row g-2">
					<div className="col-6">
						<Link to="/" className="btn btn-outline-light w-100">
							<i className="bi bi-chevron-left me-1"></i>
							Home
						</Link>
					</div>
					<div className="col-6">
						<button className="btn btn-outline-light w-100" onClick={handleDownloadKeys}>
							<i className="bi bi-download me-1 keys-link"></i>
							Keys
						</button>
					</div>
					<div className="col-6">
						<a
							href="https://docs.waveassist.io"
							target="_blank"
							rel="noopener noreferrer"
							className="btn btn-outline-light w-100"
						>
							<i className="bi bi-journal-code me-1"></i>
							Docs
						</a>
					</div>
					<div className="col-6">
						<button className="btn btn-outline-light w-100" onClick={handleLogout}>
							<i className="bi bi-box-arrow-right me-1"></i>
							Logout
						</button>
					</div>
				</div>
			</div>
		</div>
	);
};

export default Sidebar;
