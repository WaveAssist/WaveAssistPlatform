import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import "bootstrap/dist/css/bootstrap.min.css"; // Import Bootstrap CSS

import { ToastProvider } from "./utils/toast_context.tsx";
import { PostHogProvider } from "posthog-js/react";
import { captureBrandParam, applyBrandToDocument, getBrand } from "./config/branding.tsx";
import { TELEMETRY_ENABLED } from "./config/runtime";

// Resolve the brand and stamp <html data-brand> + tab title before React mounts.
// (captureBrandParam is a no-op in production; VITE_BRAND is authoritative there.)
captureBrandParam();
applyBrandToDocument();

const appTree = (
	<ToastProvider>
		<App />
	</ToastProvider>
);

ReactDOM.createRoot(document.getElementById("root")!).render(
	<React.StrictMode>
		{TELEMETRY_ENABLED ? (
			<PostHogProvider
				apiKey={getBrand().posthogKey}
				options={{
					api_host: "https://us.i.posthog.com",
					debug: import.meta.env.MODE === "development",
					loaded: (ph) => ph.register({ brand: getBrand().id }),
				}}>
				{appTree}
			</PostHogProvider>
		) : (
			appTree
		)}
	</React.StrictMode>
);
