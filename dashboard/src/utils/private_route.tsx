import React, { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { usePostHog } from "posthog-js/react";

interface PrivateRouteProps {
	component: React.ComponentType<any>;
	layout?: React.ComponentType<any>;
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ component: Component, layout: Layout, ...rest }) => {
	const location = useLocation();
	const posthog = usePostHog();
	const isAuthenticated = !!localStorage.getItem("uid");

	useEffect(() => {
		// Fire PostHog identify event for already authenticated users
		if (isAuthenticated && posthog) {
			try {
				const userData = localStorage.getItem("user_data");
				if (userData) {
					const user = JSON.parse(userData);
					const uid = user.uid || localStorage.getItem("uid");
					const email = user.username || user.email || "";
					const name = user.name || "";

					if (uid) {
						posthog.identify(uid, { email, name, uid });
					}
				}
			} catch (error) {
				console.error("Error identifying user in PrivateRoute:", error);
			}
		}
	}, [isAuthenticated, posthog]);

	if (!isAuthenticated) {
		const redirectPath = location.pathname + location.search;
		return <Navigate to={`/login?redirect=${encodeURIComponent(redirectPath)}`} state={{ from: location }} />;
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
