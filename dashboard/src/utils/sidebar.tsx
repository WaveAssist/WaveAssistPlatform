// src/Sidebar.js
import { Link, useLocation, useNavigate } from "react-router-dom";
import "./sidebar.css";
import GreenLogo from "../assets/Logo/GreenLogo_Full_white_no_w.png";

const Sidebar = () => {
	const location = useLocation();
	const navigate = useNavigate();

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
		<div className="side-div d-flex flex-column flex-shrink-0 p-3 vh-100">
			<div className="d-flex flex-column align-items-center mb-4 me-md-auto text-white text-decoration-none w-100">
				<a href="/">
					<img src={GreenLogo} className="wp_logo" alt="WavePredict Logo" />
				</a>
			</div>

			<ul className="nav nav-pills flex-column mb-auto">
				<li className="nav-item">
					<Link to="/manage/nodes" className={`nav-link ${location.pathname === "/manage/nodes" ? "active" : "text-white"} mb-1`} aria-current="page">
						<i className="bi bi-bezier2 me-2"></i>
						Nodes
					</Link>
				</li>
				<li className="nav-item">
					<Link to="/manage/variables" className={`nav-link ${location.pathname === "/manage/variables" ? "active" : "text-white"} mb-1`}>
						<i className="bi bi-table me-2"></i>
						Variables
					</Link>
				</li>
				<li className="nav-item">
					<Link to="/manage/environments" className={`nav-link ${location.pathname === "/manage/environments" ? "active" : "text-white"} mb-1`}>
						<i className="bi bi-stack me-2"></i>
						Environments
					</Link>
				</li>

				<li className="nav-item">
					<Link to="/manage/deployments" className={`nav-link ${location.pathname === "/manage/deployments" ? "active" : "text-white"} mb-1`}>
						<i className="bi bi-cloud-arrow-up-fill me-2"></i>
						Deployments
					</Link>
				</li>

				<li className="nav-item">
					<Link to="/manage/data-view" className={`nav-link ${location.pathname === "/manage/data-view" ? "active" : "text-white"} mb-1`}>
						<i className="bi bi-grid-1x2-fill me-2"></i>
						Data Viewer
					</Link>
				</li>
			</ul>
			<div>
				<button className="btn btn-outline-light w-100" type="button" onClick={handleLogout}>
					<i className="bi bi-box-arrow-right me-2"></i>
					Logout
				</button>
			</div>
		</div>
	);
};

export default Sidebar;
