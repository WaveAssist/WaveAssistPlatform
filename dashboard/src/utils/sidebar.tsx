// src/Sidebar.js
import { Link, useLocation } from "react-router-dom";
import "./sidebar.css";
import GreenLogo from "../assets/Logo/GreenLogo_Full_white_no_w.png";
import WavePredictLogo from "../assets/Logo/Wave_Predict_W_Logo.png";
import { useEffect, useState } from "react";
import Joyride, { Step } from "react-joyride";
interface SidebarProps {
	isOpen: boolean;
	onClose: () => void;
	planName?: string;
	isCollapsed?: boolean;
	onToggleCollapse?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose, planName, isCollapsed = false, onToggleCollapse }) => {
	const location = useLocation();
	const [runTour, setRunTour] = useState(false);

	// Get plan name from localStorage if not provided as prop
	const currentPlanName = planName || localStorage.getItem("plan_name") || "operator";

	// Determine which sections should be visible based on plan
	const isBuilderOrEditorPlan = currentPlanName === "builder" || currentPlanName === "editor";

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

	const handleNavClick = () => {
		if (window.innerWidth < 768) {
			onClose();
		}
	};

	return (
		<div className={`side-div d-flex flex-column flex-shrink-0 p-3 ${isOpen ? "" : "d-none d-md-flex"} ${isCollapsed ? "sidebar-collapsed" : ""}`}>
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

			<div className="d-flex flex-column me-md-auto w-100">
				{!isCollapsed ? (
					<div className="d-flex align-items-center justify-content-between">
						<a href="/" className="d-flex align-items-center">
							<img src={GreenLogo} className="wp_logo" alt="WavePredict Logo" />
						</a>
						<div className="d-flex gap-2">
							{window.innerWidth >= 768 && onToggleCollapse && (
								<button className="btn btn-outline-secondary btn-sm collapse-btn" onClick={onToggleCollapse} title="Collapse sidebar">
									<i className="bi bi-chevron-left"></i>
								</button>
							)}
							<button className="btn btn-outline-light d-md-none" onClick={onClose}>
								<i className="bi bi-x-lg"></i>
							</button>
						</div>
					</div>
				) : (
					<div className="d-flex flex-column align-items-center collapsed-header">
						<div className="mb-2 logo-container">
							<a href="/">
								<img src={WavePredictLogo} className="wp_logo_collapsed" alt="WavePredict Logo" />
							</a>
							<button className="btn btn-outline-secondary btn-sm expand-btn" onClick={onToggleCollapse} title="Expand sidebar">
								<i className="bi bi-chevron-right"></i>
							</button>
						</div>
					</div>
				)}
			</div>

			<ul className="nav nav-pills flex-column">
				{/* Assistant - Visible for all plans */}
				{!isCollapsed && (
					<li
						className="nav-item mb-1 text-uppercase small ps-2"
						style={{ color: "#ffffff80", fontSize: "11px", letterSpacing: "0.05em", paddingTop: "48px" }}>
						Usage
					</li>
				)}
				<li className="nav-item">
					<Link
						to="/manage/assistant"
						className={`nav-link ${location.pathname === "/manage/assistant" ? "active" : "text-white"} mb-1 ${
							isCollapsed ? "collapsed-nav-link" : ""
						}`}
						onClick={handleNavClick}
						title={isCollapsed ? "Assistant" : ""}>
						{isCollapsed ? (
							<>
								<div className="nav-icon">
									<i className="bi bi-bullseye"></i>
								</div>
								<span>Assistant</span>
							</>
						) : (
							<>
								<i className="bi bi-bullseye me-2"></i>
								Assistant
							</>
						)}
					</Link>
				</li>

				{/* Runs - Visible for all plans */}
				<li className="nav-item">
					<Link
						to="/manage/runs"
						className={`nav-link ${location.pathname === "/manage/runs" ? "active" : "text-white"} mb-1 ${isCollapsed ? "collapsed-nav-link" : ""}`}
						onClick={handleNavClick}
						title={isCollapsed ? "Runs" : ""}>
						{isCollapsed ? (
							<>
								<div className="nav-icon">
									<i className="bi bi-bar-chart-steps"></i>
								</div>
								<span>Runs</span>
							</>
						) : (
							<>
								<i className="bi bi-bar-chart-steps me-2"></i>
								Runs
							</>
						)}
					</Link>
				</li>

				{/* Deployments - Visible for all plans */}
				<li className="nav-item">
					<Link
						to="/manage/deployments"
						className={`nav-link ${location.pathname === "/manage/deployments" ? "active" : "text-white"} mb-1 ${
							isCollapsed ? "collapsed-nav-link" : ""
						}`}
						onClick={handleNavClick}
						title={isCollapsed ? "Deployments" : ""}>
						{isCollapsed ? (
							<>
								<div className="nav-icon">
									<i className="bi bi-cloud-arrow-up-fill"></i>
								</div>
								<span>Deployments</span>
							</>
						) : (
							<>
								<i className="bi bi-cloud-arrow-up-fill me-2"></i>
								Deployments
							</>
						)}
					</Link>
				</li>

				{/* Environments - Locked for operators, visible for builder/editor plans */}

				{/* Credits - Visible for all plans */}
				<li className="nav-item">
					<Link
						to="/manage/credits"
						className={`nav-link ${location.pathname === "/manage/credits" ? "active" : "text-white"} mb-1 ${
							isCollapsed ? "collapsed-nav-link" : ""
						}`}
						onClick={handleNavClick}
						title={isCollapsed ? "Credits" : ""}>
						{isCollapsed ? (
							<>
								<div className="nav-icon">
									<i className="bi bi-credit-card"></i>
								</div>
								<span>Credits</span>
							</>
						) : (
							<>
								<i className="bi bi-credit-card me-2"></i>
								Credits
							</>
						)}
					</Link>
				</li>

				{!isCollapsed && (
					<li className="nav-item mb-1 text-uppercase small ps-2 pt-3" style={{ color: "#ffffff80", fontSize: "11px", letterSpacing: "0.05em" }}>
						Customizations
					</li>
				)}

				{/* Nodes - Locked for operators, visible for builder/editor plans */}
				<li className="nav-item">
					{isBuilderOrEditorPlan ? (
						<Link
							to="/manage/nodes"
							className={`nav-link ${location.pathname === "/manage/nodes" ? "active" : "text-white"} mb-1 ${
								isCollapsed ? "collapsed-nav-link" : ""
							}`}
							onClick={handleNavClick}>
							{isCollapsed ? (
								<>
									<div className="nav-icon">
										<i className="bi bi-bezier2"></i>
									</div>
									<span>Nodes</span>
								</>
							) : (
								<>
									<i className="bi bi-bezier2 me-2"></i>
									Nodes
								</>
							)}
						</Link>
					) : (
						<Link
							to="/manage/nodes"
							className={`nav-link text-white-50 mb-1 disabled-link ${isCollapsed ? "collapsed-nav-link" : ""}`}
							onClick={handleNavClick}
							title={isCollapsed ? "Nodes (Locked)" : ""}
							style={{ cursor: "pointer", opacity: 0.7, backgroundColor: "rgba(255, 255, 255, 0.1)", borderRadius: "6px", padding: "8px 12px" }}>
							{isCollapsed ? (
								<>
									<div className="nav-icon">
										<i className="bi bi-bezier2"></i>
									</div>
									<span>Nodes</span>
								</>
							) : (
								<>
									<i className="bi bi-bezier2 me-2"></i>
									Nodes
									<i className="bi bi-lock-fill ms-2" style={{ fontSize: "0.8rem" }}></i>
								</>
							)}
						</Link>
					)}
				</li>

				{/* Variables - Locked for operators, visible for builder/editor plans */}
				<li className="nav-item">
					{isBuilderOrEditorPlan ? (
						<Link
							to="/manage/variables"
							className={`nav-link ${location.pathname === "/manage/variables" ? "active" : "text-white"} mb-1 variables-link ${
								isCollapsed ? "collapsed-nav-link" : ""
							}`}
							onClick={handleNavClick}>
							{isCollapsed ? (
								<>
									<div className="nav-icon">
										<i className="bi bi-table"></i>
									</div>
									<span>Variables</span>
								</>
							) : (
								<>
									<i className="bi bi-table me-2"></i>
									Variables
								</>
							)}
						</Link>
					) : (
						<Link
							to="/manage/variables"
							className={`nav-link text-white-50 mb-1 disabled-link ${isCollapsed ? "collapsed-nav-link" : ""}`}
							onClick={handleNavClick}
							title={isCollapsed ? "Variables (Locked)" : ""}
							style={{ cursor: "pointer", opacity: 0.7, backgroundColor: "rgba(255, 255, 255, 0.1)", borderRadius: "6px", padding: "8px 12px" }}>
							{isCollapsed ? (
								<>
									<div className="nav-icon">
										<i className="bi bi-table"></i>
									</div>
									<span>Variables</span>
								</>
							) : (
								<>
									<i className="bi bi-table me-2"></i>
									Variables
									<i className="bi bi-lock-fill ms-2" style={{ fontSize: "0.8rem" }}></i>
								</>
							)}
						</Link>
					)}
				</li>

				{/* Packages - Locked for operators, visible for builder/editor plans */}
				<li className="nav-item">
					{isBuilderOrEditorPlan ? (
						<Link
							to="/manage/packages"
							className={`nav-link ${location.pathname === "/manage/packages" ? "active" : "text-white"} mb-1 packages-link ${
								isCollapsed ? "collapsed-nav-link" : ""
							}`}
							onClick={handleNavClick}>
							{isCollapsed ? (
								<>
									<div className="nav-icon">
										<i className="bi bi-box-fill"></i>
									</div>
									<span>Packages</span>
								</>
							) : (
								<>
									<i className="bi bi-box-fill me-2"></i>
									Packages
								</>
							)}
						</Link>
					) : (
						<Link
							to="/manage/packages"
							className={`nav-link text-white-50 mb-1 disabled-link ${isCollapsed ? "collapsed-nav-link" : ""}`}
							onClick={handleNavClick}
							style={{ cursor: "pointer", opacity: 0.7, backgroundColor: "rgba(255, 255, 255, 0.1)", borderRadius: "6px", padding: "8px 12px" }}>
							{isCollapsed ? (
								<>
									<div className="nav-icon">
										<i className="bi bi-box-fill"></i>
									</div>
									<span>Packages</span>
								</>
							) : (
								<>
									<i className="bi bi-box-fill me-2"></i>
									Packages
									<i className="bi bi-lock-fill ms-2" style={{ fontSize: "0.8rem" }}></i>
								</>
							)}
						</Link>
					)}
				</li>

				<li className="nav-item">
					{isBuilderOrEditorPlan ? (
						<Link
							to="/manage/environments"
							className={`nav-link ${location.pathname === "/manage/environments" ? "active" : "text-white"} mb-1 ${
								isCollapsed ? "collapsed-nav-link" : ""
							}`}
							onClick={handleNavClick}>
							{isCollapsed ? (
								<>
									<div className="nav-icon">
										<i className="bi bi-stack"></i>
									</div>
									<span>Environments</span>
								</>
							) : (
								<>
									<i className="bi bi-stack me-2"></i>
									Environments
								</>
							)}
						</Link>
					) : (
						<Link
							to="/manage/environments"
							className={`nav-link text-white-50 mb-1 disabled-link ${isCollapsed ? "collapsed-nav-link" : ""}`}
							onClick={handleNavClick}
							style={{ cursor: "pointer", opacity: 0.7, backgroundColor: "rgba(255, 255, 255, 0.1)", borderRadius: "6px", padding: "8px 12px" }}>
							{isCollapsed ? (
								<>
									<div className="nav-icon">
										<i className="bi bi-stack"></i>
									</div>
									<span>Environments</span>
								</>
							) : (
								<>
									<i className="bi bi-stack me-2"></i>
									Environments
									<i className="bi bi-lock-fill ms-2" style={{ fontSize: "0.8rem" }}></i>
								</>
							)}
						</Link>
					)}
				</li>

				{/* Logs - Locked for operators, visible for builder/editor plans */}
				<li className="nav-item">
					{isBuilderOrEditorPlan ? (
						<Link
							to="/manage/logs"
							className={`nav-link ${location.pathname === "/manage/logs" ? "active" : "text-white"} mb-1 logs-link ${
								isCollapsed ? "collapsed-nav-link" : ""
							}`}
							onClick={handleNavClick}>
							{isCollapsed ? (
								<>
									<div className="nav-icon">
										<i className="bi bi-file-text-fill"></i>
									</div>
									<span>Logs</span>
								</>
							) : (
								<>
									<i className="bi bi-file-text-fill me-2"></i>
									Logs
								</>
							)}
						</Link>
					) : (
						<Link
							to="/manage/logs"
							className={`nav-link text-white-50 mb-1 disabled-link ${isCollapsed ? "collapsed-nav-link" : ""}`}
							onClick={handleNavClick}
							style={{ cursor: "pointer", opacity: 0.7, backgroundColor: "rgba(255, 255, 255, 0.1)", borderRadius: "6px", padding: "8px 12px" }}>
							{isCollapsed ? (
								<>
									<div className="nav-icon">
										<i className="bi bi-file-text-fill"></i>
									</div>
									<span>Logs</span>
								</>
							) : (
								<>
									<i className="bi bi-file-text-fill me-2"></i>
									Logs
									<i className="bi bi-lock-fill ms-2" style={{ fontSize: "0.8rem" }}></i>
								</>
							)}
						</Link>
					)}
				</li>
			</ul>

			<div className="mt-auto">
				<hr className="text-white" />
				{isCollapsed ? (
					<div className="d-flex flex-column gap-2">
						<Link to="/" className="btn btn-outline-light collapsed-btn" onClick={handleNavClick} title="Back">
							<div className="nav-icon">
								<i className="bi bi-chevron-left"></i>
								<span style={{ fontSize: "0.8rem" }}>Back</span>
							</div>
						</Link>
					</div>
				) : (
					<div className="row g-2">
						<div className="col-12">
							<Link to="/" className="btn btn-outline-light w-100" onClick={handleNavClick}>
								<i className="bi bi-chevron-left me-1"></i>
								Back
							</Link>
						</div>
					</div>
				)}
			</div>
		</div>
	);
};

export default Sidebar;
