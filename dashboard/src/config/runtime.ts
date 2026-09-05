// Runtime deployment config for the dashboard, resolved from Vite build-time env.
//
// Vite compiles these into the bundle at BUILD time, so a self-hosted image is
// produced by building with the right VITE_* values (see .env.example). Every
// flag defaults to hosted-cloud behaviour, so an unconfigured build behaves
// exactly like today's SaaS dashboard.
//
//   VITE_DASHBOARD_BASE_URL  API base (already used by base_service)
//   VITE_AUTH_MODE           "firebase" (default) | "local"  (UID login, no Google)
//   VITE_TELEMETRY           "on" (default) | "off"          (PostHog/GA)
//   VITE_BILLING             "on" (default) | "off"          (upgrade/credits UI)
//   VITE_MCP_URL             overrides the Connect-MCP endpoint shown in the UI

const env = import.meta.env as Record<string, string | undefined>;

function mode(name: string, def: string): string {
	const v = env[name];
	return (v && v.trim() !== "" ? v : def).trim().toLowerCase();
}

export const AUTH_MODE = mode("VITE_AUTH_MODE", "firebase"); // firebase | local
export const IS_LOCAL_AUTH = AUTH_MODE === "local";
export const IS_PASSWORD_AUTH = AUTH_MODE === "password";
export const TELEMETRY_ENABLED = mode("VITE_TELEMETRY", "on") !== "off";
export const BILLING_ENABLED = mode("VITE_BILLING", "on") !== "off";
export const LOCAL_UID = (env.VITE_LOCAL_UID && env.VITE_LOCAL_UID.trim()) || "";
export const MCP_URL_OVERRIDE = (env.VITE_MCP_URL && env.VITE_MCP_URL.trim()) || "";

export const runtimeConfig = {
	authMode: AUTH_MODE,
	isLocalAuth: IS_LOCAL_AUTH,
	telemetryEnabled: TELEMETRY_ENABLED,
	billingEnabled: BILLING_ENABLED,
	mcpUrlOverride: MCP_URL_OVERRIDE,
	localUid: LOCAL_UID,
};
