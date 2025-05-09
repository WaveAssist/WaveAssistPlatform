import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import "bootstrap/dist/css/bootstrap.min.css"; // Import Bootstrap CSS
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown-light.min.css" />;

import { ToastProvider } from "./utils/toast_context.tsx";
import { PostHogProvider } from "posthog-js/react";

ReactDOM.createRoot(document.getElementById("root")!).render(
	<React.StrictMode>
		<PostHogProvider
			apiKey="REMOVED_CREDENTIAL"
			options={{
				api_host: "https://us.i.posthog.com",
				debug: import.meta.env.MODE === "development",
			}}>
			<ToastProvider>
				<App />
			</ToastProvider>
		</PostHogProvider>
	</React.StrictMode>
);
