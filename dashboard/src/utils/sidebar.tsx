// src/Sidebar.js
import { Link, useLocation, useNavigate } from "react-router-dom";
import "./sidebar.css";
import GreenLogo from "../assets/Logo/GreenLogo_Full_white_no_w.png";
import { useEffect, useState } from "react";
import Joyride, { Step } from "react-joyride";

interface SidebarProps {
	isOpen: boolean;
	onClose: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
	const location = useLocation();
	const navigate = useNavigate();
	const [runTour, setRunTour] = useState(false);

	useEffect(() => {
		const isNewUser = localStorage.getItem("is_new_user");
		const modulesTour = localStorage.getItem("modules_tour");

		if (modulesTour === null && isNewUser === "true") {
			setRunTour(true);
			localStorage.setItem("is_new_user", "false");
			localStorage.setItem("modules_tour", "true");
		}
	}, []);

	const steps: Step[] = [
		{
			target: ".variables-link",
			content: "View and manage your variables here.",
		},
		{
			target: ".packages-link",
			content: "Manage all your installed packages from here.",
		},
		{
			target: ".logs-link",
			content: "View detailed logs for all your executed workflows.",
		},
		{
			target: ".keys-link",
			content: "Download your keys to integrate with external services.",
			locale: { last: "Got it" },
		},
	];

	const handleLogout = () => {
		localStorage.removeItem("uid");
		localStorage.removeItem("projects_array");
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

		const csvContent = "data:text/csv;charset=utf-8," + filteredEntries.map(([key, value]) => `${key},${value}`).join("\n");

		const encodedUri = encodeURI(csvContent);
		const link = document.createElement("a");
		link.setAttribute("href", encodedUri);
		link.setAttribute("download", "waveassist_keys.csv");
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
	};

	const handleNavClick = () => {
		if (window.innerWidth < 768) {
			onClose();
		}
	};

	return (
		<div className={`side-div d-flex flex-column flex-shrink-0 p-3 ${isOpen ? "" : "d-none d-md-flex"}`}>
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

			<div className="d-flex align-items-center justify-content-between me-md-auto w-100">
				<div className="d-flex flex-column align-items-start">
					<a href="/">
						<img src={GreenLogo} className="wp_logo" alt="WavePredict Logo" />
					</a>
				</div>
				<button className="btn btn-outline-light d-md-none" onClick={onClose}>
					<i className="bi bi-x-lg"></i>
				</button>
			</div>

			<ul className="nav nav-pills flex-column mb-4 mt-4">
				<li className="nav-item">
					<Link
						to="/manage/nodes"
						className={`nav-link ${location.pathname === "/manage/nodes" ? "active" : "text-white"} mb-1`}
						onClick={handleNavClick}>
						<i className="bi bi-bezier2 me-2"></i>
						Nodes
					</Link>
				</li>
				<li className="nav-item">
					<Link
						to="/manage/variables"
						className={`nav-link ${location.pathname === "/manage/variables" ? "active" : "text-white"} mb-1 variables-link`}
						onClick={handleNavClick}>
						<i className="bi bi-table me-2"></i>
						Variables
					</Link>
				</li>
				<li className="nav-item">
					<Link
						to="/manage/packages"
						className={`nav-link ${location.pathname === "/manage/packages" ? "active" : "text-white"} mb-1 packages-link`}
						onClick={handleNavClick}>
						<i className="bi bi-box-fill me-2"></i>
						Packages
					</Link>
				</li>
				<li className="nav-item">
					<Link
						to="/manage/runs"
						className={`nav-link ${location.pathname === "/manage/runs" ? "active" : "text-white"} mb-1`}
						onClick={handleNavClick}>
						<i className="bi bi-bar-chart-steps me-2"></i>
						Runs
					</Link>
				</li>
				<li className="nav-item">
					<Link
						to="/manage/deployments"
						className={`nav-link ${location.pathname === "/manage/deployments" ? "active" : "text-white"} mb-1`}
						onClick={handleNavClick}>
						<i className="bi bi-cloud-arrow-up-fill me-2"></i>
						Deployments
					</Link>
				</li>
				<li className="nav-item">
					<Link
						to="/manage/environments"
						className={`nav-link ${location.pathname === "/manage/environments" ? "active" : "text-white"} mb-1`}
						onClick={handleNavClick}>
						<i className="bi bi-stack me-2"></i>
						Environments
					</Link>
				</li>
				<li className="nav-item">
					<Link
						to="/manage/logs"
						className={`nav-link ${location.pathname === "/manage/logs" ? "active" : "text-white"} mb-1 logs-link`}
						onClick={handleNavClick}>
						<i className="bi bi-file-text-fill me-2"></i>
						Logs
					</Link>
				</li>

				<li className="nav-item mb-1 text-uppercase small ps-2 pt-3" style={{ color: "#ffffff80", fontSize: "11px", letterSpacing: "0.05em" }}>
					Resources
				</li>

				<li className="nav-item" style={{ fontSize: "15px", marginBottom: "3px" }}>
					<a href="https://waveassist.io/assistants" target="_blank" rel="noopener noreferrer" className="nav-link text-white fw-normal py-1">
						<i className="bi bi-bookmark-check-fill me-2"></i>
						Assistants
						<i className="bi bi-box-arrow-up-right ms-2" style={{ fontSize: "14px" }}></i>
					</a>
				</li>
				<li className="nav-item" style={{ fontSize: "15px" }}>
					<a href="https://docs.waveassist.io" target="_blank" rel="noopener noreferrer" className="nav-link text-white fw-normal py-1">
						<i className="bi bi-file-earmark-code-fill me-2"></i>
						Docs
						<i className="bi bi-box-arrow-up-right ms-2" style={{ fontSize: "14px" }}></i>
					</a>
				</li>
			</ul>

			<div className="mt-auto">
				<hr className="text-white" />
				<div className="row g-2">
					<div className="col-6">
						<Link to="/" className="btn btn-outline-light w-100" onClick={handleNavClick}>
							<i className="bi bi-chevron-left me-1"></i>
							Home
						</Link>
					</div>
					<div className="col-6">
						<button
							className="btn btn-outline-light w-100 keys-link"
							onClick={() => {
								handleDownloadKeys();
								handleNavClick();
							}}>
							<i className="bi bi-download me-1"></i>
							Keys
						</button>
					</div>

					<div className="col-12">
						<button
							className="btn btn-outline-light w-100"
							onClick={() => {
								handleLogout();
								handleNavClick();
							}}>
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
