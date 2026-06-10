// src/Sidebar.js
import { Link, useLocation } from "react-router-dom";
import "./sidebar.css";
import GreenLogo from "../assets/Logo/GreenLogo_Full_white_no_w.png";
import WavePredictLogo from "../assets/Logo/Wave_Predict_W_Logo.png";
interface SidebarProps {
	isOpen: boolean;
	onClose: () => void;
	planName?: string;
	isCollapsed?: boolean;
	onToggleCollapse?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose, planName: _planName, isCollapsed = false, onToggleCollapse }) => {
	const location = useLocation();
	const handleNavClick = () => {
		if (window.innerWidth < 768) {
			onClose();
		}
	};

	return (
		<div className={`side-div d-flex flex-column flex-shrink-0 p-3 ${isOpen ? "" : "d-none d-md-flex"} ${isCollapsed ? "sidebar-collapsed" : ""}`}>
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
						Modules
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

				{/* Knowledge - Visible for all plans */}
				<li className="nav-item">
					<Link
						to="/manage/knowledge"
						className={`nav-link ${location.pathname === "/manage/knowledge" ? "active" : "text-white"} mb-1 ${
							isCollapsed ? "collapsed-nav-link" : ""
						}`}
						onClick={handleNavClick}
						title={isCollapsed ? "Knowledge" : ""}>
						{isCollapsed ? (
							<>
								<div className="nav-icon">
									<i className="bi bi-lightbulb"></i>
								</div>
								<span>Knowledge</span>
							</>
						) : (
							<>
								<i className="bi bi-lightbulb me-2"></i>
								Knowledge
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

				{/* Billing - Visible for all plans */}
				<li className="nav-item">
					<Link
						to="/manage/credits"
						className={`nav-link ${location.pathname === "/manage/credits" ? "active" : "text-white"} mb-1 ${
							isCollapsed ? "collapsed-nav-link" : ""
						}`}
						onClick={handleNavClick}
						title={isCollapsed ? "Billing" : ""}>
						{isCollapsed ? (
							<>
								<div className="nav-icon">
									<i className="bi bi-credit-card"></i>
								</div>
								<span>Billing</span>
							</>
						) : (
							<>
								<i className="bi bi-credit-card me-2"></i>
								Billing
							</>
						)}
					</Link>
				</li>

				{/* Divider between Modules and Customizations - only in collapsed view */}
				{isCollapsed && (
					<li className="nav-item nav-divider-collapsed" aria-hidden="true">
						<div className="sidebar-group-divider" />
					</li>
				)}

				{!isCollapsed && (
					<li className="nav-item mb-1 text-uppercase small ps-2 pt-3" style={{ color: "#ffffff80", fontSize: "11px", letterSpacing: "0.05em" }}>
						Customizations
					</li>
				)}

				{/* Nodes - Visible and unlocked for all plans */}
				<li className="nav-item">
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
				</li>

				{/* Variables / Environments / Packages / Logs are intentionally hidden from sidebar. */}

			</ul>

			<div className="mt-auto">
				<hr className="text-white" />
				{isCollapsed ? (
					<div className="d-flex flex-column gap-2">
						<Link to="/" className="btn btn-outline-light collapsed-btn" onClick={handleNavClick} title="Back">
							<div className="nav-icon">
								<i className="bi bi-chevron-left" style={{ fontSize: "1rem" }}></i>
								<span style={{ fontSize: "0.75rem" }}>Back</span>
							</div>
						</Link>
					</div>
				) : (
					<div className="row g-2">
						<div className="col-12">
							<Link to="/" className="btn btn-outline-light w-100" onClick={handleNavClick} style={{ fontSize: "0.75rem", whiteSpace: "nowrap" }}>
								<i className="bi bi-chevron-left me-1" style={{ fontSize: "1rem" }}></i>
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
