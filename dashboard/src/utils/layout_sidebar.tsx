// src/Layout.tsx
import React, { ReactNode, useState, useEffect } from "react";
import Sidebar from "./sidebar";
import NavbarComponent from "./navbar";
import { Container } from "react-bootstrap";
import RefreshContext from "./RefreshContext";
import WizardContext from "./WizardContext";

interface LayoutProps {
	children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
	const [shouldRefresh, setShouldRefresh] = useState(false);
	const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth >= 768);

	useEffect(() => {
		const handleResize = () => {
			setSidebarOpen(window.innerWidth >= 768);
		};
		window.addEventListener("resize", handleResize);
		return () => window.removeEventListener("resize", handleResize);
	}, []);

	// Function to trigger refresh
	const triggerRefresh = () => {
		setShouldRefresh((prev) => !prev);
	};

	// Function to trigger wizard
	const triggerWizard = () => {
		// This will be handled by the nodes component
		window.dispatchEvent(new CustomEvent('triggerWizard'));
	};

	return (
		<RefreshContext.Provider value={{ shouldRefresh, triggerRefresh }}>
			<WizardContext.Provider value={{ triggerWizard }}>
				<div className="d-flex vh-100 position-relative">
					<Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
					<div className="d-flex flex-column flex-grow-1 main-content">
						<NavbarComponent onToggleSidebar={() => setSidebarOpen((o) => !o)} />
						<Container fluid className="flex-grow-1 p-3">
							{children}
						</Container>
					</div>
				</div>
			</WizardContext.Provider>
		</RefreshContext.Provider>
	);
};

export default Layout;
