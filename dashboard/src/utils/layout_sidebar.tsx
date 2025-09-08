// src/Layout.tsx
import React, { ReactNode, useState, useEffect } from "react";
import Sidebar from "./sidebar";
import NavbarComponent from "./navbar";
import { Container } from "react-bootstrap";
import RefreshContext from "./RefreshContext";

interface LayoutProps {
	children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
	const [shouldRefresh, setShouldRefresh] = useState(false);
	const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth >= 768);
	const [sidebarCollapsed, setSidebarCollapsed] = useState(window.innerWidth >= 768);

	// Get plan name from localStorage
	const planName = localStorage.getItem("plan_name") || undefined;

	useEffect(() => {
		const handleResize = () => {
			const isDesktop = window.innerWidth >= 768;
			setSidebarOpen(isDesktop);
			// On mobile, always show expanded sidebar when open
			if (!isDesktop) {
				setSidebarCollapsed(false);
			}
		};
		window.addEventListener("resize", handleResize);
		return () => window.removeEventListener("resize", handleResize);
	}, []);

	// Function to trigger refresh
	const triggerRefresh = () => {
		setShouldRefresh((prev) => !prev);
	};

	return (
		<RefreshContext.Provider value={{ shouldRefresh, triggerRefresh }}>
			<div className="d-flex vh-100 position-relative">
				<Sidebar
					isOpen={sidebarOpen}
					onClose={() => setSidebarOpen(false)}
					planName={planName}
					isCollapsed={sidebarCollapsed}
					onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
				/>
				<div className={`d-flex flex-column flex-grow-1 main-content ${sidebarCollapsed && window.innerWidth >= 768 ? "sidebar-collapsed" : ""}`}>
					<NavbarComponent onToggleSidebar={() => setSidebarOpen((o) => !o)} />
					<Container fluid className="flex-grow-1 p-3">
						{children}
					</Container>
				</div>
			</div>
		</RefreshContext.Provider>
	);
};

export default Layout;
