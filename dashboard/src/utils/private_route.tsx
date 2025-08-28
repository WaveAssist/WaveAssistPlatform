import React, { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { auth } from "../components/firebase";
import { onAuthStateChanged } from "firebase/auth";

interface PrivateRouteProps {
	component: React.ComponentType<any>;
	layout?: React.ComponentType<any>;
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ component: Component, layout: Layout, ...rest }) => {
	const location = useLocation();
	const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

	useEffect(() => {
		const unsubscribe = onAuthStateChanged(auth, (user) => {
			setIsAuthenticated(!!user);

			// Sync with localStorage for backward compatibility
			if (user) {
				localStorage.setItem("uid", user.uid);
			} else {
				localStorage.removeItem("uid");
			}
		});

		return () => unsubscribe();
	}, []);

	// Show loading while checking authentication
	if (isAuthenticated === null) {
		return <div>Loading...</div>;
	}

	if (!isAuthenticated) {
		return <Navigate to="/login" state={{ from: location }} />;
	}

	const RenderComponent = Layout ? (
		<Layout>
			<Component {...rest} />
		</Layout>
	) : (
		<Component {...rest} />
	);

	return RenderComponent;
};

export default PrivateRoute;
