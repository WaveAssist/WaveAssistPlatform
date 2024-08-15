// src/Layout.tsx
import React, { ReactNode, useState } from "react";
import Sidebar from "./sidebar";
import NavbarComponent from "./navbar";
import { Container } from "react-bootstrap";
import RefreshContext from "./RefreshContext";

interface LayoutProps {
	children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
	const [shouldRefresh, setShouldRefresh] = useState(false);

	// Function to trigger refresh
	const triggerRefresh = () => {
		setShouldRefresh((prev) => !prev);
	};

	return (
		<RefreshContext.Provider value={{ shouldRefresh, triggerRefresh }}>
			<div className="d-flex vh-100">
				<Sidebar />
				<div className="d-flex flex-column flex-grow-1">
					<NavbarComponent />
					<Container fluid className="flex-grow-1 p-3">
						{children}
					</Container>
				</div>
			</div>
		</RefreshContext.Provider>
	);
};

export default Layout;
