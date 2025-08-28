import React from "react";
import { Navigate, useLocation } from "react-router-dom";

interface PrivateRouteProps {
	component: React.ComponentType<any>;
	layout?: React.ComponentType<any>;
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ component: Component, layout: Layout, ...rest }) => {
	const location = useLocation();
	const isAuthenticated = !!localStorage.getItem("uid");

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
