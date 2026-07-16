import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import "bootstrap/dist/css/bootstrap.min.css"; // Import Bootstrap CSS

import { ToastProvider } from "./utils/toast_context.tsx";
import { PostHogProvider } from "posthog-js/react";
import { captureBrandParam, applyBrandToDocument, getBrand } from "./config/branding.tsx";

// Resolve the brand and stamp <html data-brand> + tab title before React mounts.
// (captureBrandParam is a no-op in production; VITE_BRAND is authoritative there.)
captureBrandParam();
applyBrandToDocument();

ReactDOM.createRoot(document.getElementById("root")!).render(
	<React.StrictMode>
		<PostHogProvider
			apiKey={getBrand().posthogKey}
			options={{
				api_host: "https://us.i.posthog.com",
				debug: import.meta.env.MODE === "development",
				// Stamp `brand` on every event + pageview so each brand's PostHog project can be
				// segmented by brand (no per-call brand hacks needed).
				loaded: (ph) => ph.register({ brand: getBrand().id }),
			}}>
			<ToastProvider>
				<App />
			</ToastProvider>
		</PostHogProvider>
	</React.StrictMode>
);
