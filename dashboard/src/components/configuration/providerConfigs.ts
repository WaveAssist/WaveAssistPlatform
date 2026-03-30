export type AuthType = "oauth" | "api_key";

export interface ProviderConfig {
	name: string;
	displayName: string;
	description: string;
	brandColor: string;
	iconLetter?: string;
	iconImage?: string;
	hasSelectResources: boolean;
	selectResourcesLabel?: string;
	hasManualToken: boolean;
	manualTokenPlaceholder?: string;
	manualTokenLabel?: string;
	manualTokenHelp?: string;
	manualTokenHelpLinkText?: string;
	manualTokenHelpLinkUrl?: string;
	validateToken?: (token: string) => string;
	authType: AuthType;
}

const validateGitHubToken = (token: string): string => {
	if (!token) {
		return "";
	}

	const tokenTypes = [
		{ prefix: "ghp_", length: 40 },
		{ prefix: "gho_", length: 40 },
		{ prefix: "github_pat_", length: 93 },
		{ prefix: "ghu_", length: 40 },
		{ prefix: "ghs_", length: 40 },
		{ prefix: "ghr_", length: 40 },
	];

	const matchingType = tokenTypes.find((type) => token.startsWith(type.prefix));

	if (!matchingType || token.length !== matchingType.length) {
		return "Please enter a valid GitHub Access Token";
	}

	return "";
};

export const PROVIDER_CONFIGS: Record<string, ProviderConfig> = {
	// ─── CRM & Sales ────────────────────────────────────────

	salesforce: {
		name: "salesforce",
		displayName: "Salesforce",
		description: "Connect Salesforce to access leads, accounts, and opportunities",
		brandColor: "#00A1E0",
		hasSelectResources: false,
		hasManualToken: true,
		manualTokenPlaceholder: "00D...",
		manualTokenLabel: "Access Token",
		manualTokenHelp: "Enter your Salesforce connected app access token or session ID.",
		authType: "oauth",
	},

	pipedrive: {
		name: "pipedrive",
		displayName: "Pipedrive",
		description: "Connect Pipedrive to access sales pipeline and leads",
		brandColor: "#017737",
		hasSelectResources: false,
		hasManualToken: true,
		manualTokenPlaceholder: "Enter API token...",
		manualTokenLabel: "API Token",
		manualTokenHelp: "Find your API token in Pipedrive Settings > Personal preferences > API.",
		authType: "oauth",
	},

	hubspot: {
		name: "hubspot",
		displayName: "HubSpot",
		description: "Connect HubSpot to share specific lists with this assistant.",
		brandColor: "#FF7A59",
		iconImage: "/providers/hubspot.png",
		hasSelectResources: false,
		hasManualToken: true,
		manualTokenPlaceholder: "pat-xxxx...",
		manualTokenLabel: "Access Token",
		manualTokenHelp:
			"Use a HubSpot Private App token with permission to read lists/contacts. You can always rotate or revoke this token from HubSpot.",
		authType: "oauth",
	},

	// ─── Support & Helpdesk ─────────────────────────────────

	zendesk: {
		name: "zendesk",
		displayName: "Zendesk",
		description: "Connect Zendesk to access support tickets and knowledge base",
		brandColor: "#03363D",
		hasSelectResources: false,
		hasManualToken: true,
		manualTokenPlaceholder: "Enter API token...",
		manualTokenLabel: "API Token",
		manualTokenHelp: "Find your API token in Zendesk Admin > Channels > API. Format: email/token:api_token",
		authType: "api_key",
	},

	intercom: {
		name: "intercom",
		displayName: "Intercom",
		description: "Connect Intercom to access customer conversations and events",
		brandColor: "#286EFA",
		hasSelectResources: false,
		hasManualToken: true,
		manualTokenPlaceholder: "Enter access token...",
		manualTokenLabel: "Access Token",
		manualTokenHelp: "Create an access token from your Intercom Developer Hub app.",
		authType: "oauth",
	},

	// ─── Communication ──────────────────────────────────────

	slack: {
		name: "slack",
		displayName: "Slack",
		description: "Connect Slack to access channel messages and threads",
		brandColor: "#4A154B",
		iconImage: "/providers/slack.png",
		hasSelectResources: true,
		selectResourcesLabel: "Select Channels",
		hasManualToken: true,
		manualTokenPlaceholder: "xoxb-...",
		manualTokenLabel: "Bot Token",
		manualTokenHelp: "Enter your Slack Bot User OAuth Token (starts with xoxb-).",
		authType: "oauth",
	},

	discord: {
		name: "discord",
		displayName: "Discord",
		description: "Connect Discord to access server messages and channels",
		brandColor: "#5865F2",
		hasSelectResources: true,
		selectResourcesLabel: "Select Servers",
		hasManualToken: true,
		manualTokenPlaceholder: "Enter bot token...",
		manualTokenLabel: "Bot Token",
		manualTokenHelp: "Enter your Discord bot token from the Developer Portal.",
		authType: "oauth",
	},

	gmail: {
		name: "gmail",
		displayName: "Gmail",
		description: "Connect Gmail to access email threads and attachments",
		brandColor: "#EA4335",
		hasSelectResources: false,
		hasManualToken: false,
		authType: "oauth",
	},

	outlook: {
		name: "outlook",
		displayName: "Outlook",
		description: "Connect Outlook to access emails and calendar events",
		brandColor: "#0078D4",
		hasSelectResources: false,
		hasManualToken: false,
		authType: "oauth",
	},

	whatsapp: {
		name: "whatsapp",
		displayName: "WhatsApp",
		description: "Connect WhatsApp via Twilio to receive incoming messages",
		brandColor: "#25D366",
		hasSelectResources: false,
		hasManualToken: true,
		manualTokenPlaceholder: "ACXXXXXXXX:your_auth_token",
		manualTokenLabel: "Twilio Credentials",
		manualTokenHelp: "Format: Account_SID:Auth_Token. Find both in your Twilio Console dashboard.",
		authType: "api_key",
	},

	// ─── Knowledge & Docs ───────────────────────────────────

	notion: {
		name: "notion",
		displayName: "Notion",
		description: "Connect Notion to access pages, databases, and wikis",
		brandColor: "#000000",
		hasSelectResources: true,
		selectResourcesLabel: "Select Pages",
		hasManualToken: true,
		manualTokenPlaceholder: "ntn_...",
		manualTokenLabel: "Integration Token",
		manualTokenHelp: "Create an internal integration at notion.so/my-integrations and paste the secret token.",
		authType: "oauth",
	},

	google_drive: {
		name: "google_drive",
		displayName: "Google Drive",
		description: "Connect Google Drive to access docs, sheets, and PDFs",
		brandColor: "#0F9D58",
		iconLetter: "GD",
		hasSelectResources: true,
		selectResourcesLabel: "Select Files",
		hasManualToken: false,
		authType: "oauth",
	},

	confluence: {
		name: "confluence",
		displayName: "Confluence",
		description: "Connect Confluence to access team docs and knowledge bases",
		brandColor: "#1868DB",
		hasSelectResources: true,
		selectResourcesLabel: "Select Spaces",
		hasManualToken: true,
		manualTokenPlaceholder: "Enter API token...",
		manualTokenLabel: "API Token",
		manualTokenHelp: "Generate an API token at id.atlassian.com/manage-profile/security/api-tokens.",
		authType: "oauth",
	},

	// ─── Data & Databases ───────────────────────────────────

	airtable: {
		name: "airtable",
		displayName: "Airtable",
		description: "Connect Airtable to access bases, records, and views",
		brandColor: "#18BFFF",
		hasSelectResources: false,
		hasManualToken: true,
		manualTokenPlaceholder: "pat...",
		manualTokenLabel: "Personal Access Token",
		manualTokenHelp: "Create a personal access token at airtable.com/create/tokens with data.records:read scope.",
		authType: "api_key",
	},

	postgresql: {
		name: "postgresql",
		displayName: "PostgreSQL",
		description: "Connect to a PostgreSQL database for direct read access",
		brandColor: "#336791",
		hasSelectResources: false,
		hasManualToken: true,
		manualTokenPlaceholder: "postgresql://user:pass@host:5432/dbname",
		manualTokenLabel: "Connection String",
		manualTokenHelp: "Enter your PostgreSQL connection URI.",
		authType: "api_key",
	},

	// ─── E-commerce & Payments ──────────────────────────────

	shopify: {
		name: "shopify",
		displayName: "Shopify",
		description: "Connect Shopify to access orders, products, and customers",
		brandColor: "#96BF48",
		hasSelectResources: false,
		hasManualToken: true,
		manualTokenPlaceholder: "shpat_...",
		manualTokenLabel: "Admin API Access Token",
		manualTokenHelp: "Create a custom app in your Shopify admin panel and use the Admin API access token.",
		authType: "api_key",
	},

	stripe: {
		name: "stripe",
		displayName: "Stripe",
		description: "Connect Stripe to access payments, subscriptions, and invoices",
		brandColor: "#635BFF",
		hasSelectResources: false,
		hasManualToken: true,
		manualTokenPlaceholder: "rk_live_...",
		manualTokenLabel: "Restricted API Key",
		manualTokenHelp: "Create a restricted key with read-only permissions in Stripe Dashboard > Developers > API keys.",
		authType: "api_key",
	},

	// ─── Dev & Project Management ───────────────────────────

	jira: {
		name: "jira",
		displayName: "Jira",
		description: "Connect Jira to access tickets, projects, and sprints",
		brandColor: "#0052CC",
		hasSelectResources: true,
		selectResourcesLabel: "Select Projects",
		hasManualToken: true,
		manualTokenPlaceholder: "Enter API token...",
		manualTokenLabel: "API Token",
		manualTokenHelp: "Generate an API token at id.atlassian.com/manage-profile/security/api-tokens.",
		authType: "oauth",
	},

	linear: {
		name: "linear",
		displayName: "Linear",
		description: "Connect Linear to access issues, cycles, and project tracking",
		brandColor: "#5E6AD2",
		iconImage: "/providers/linear.png",
		hasSelectResources: true,
		selectResourcesLabel: "Select Teams",
		hasManualToken: true,
		manualTokenPlaceholder: "lin_api_...",
		manualTokenLabel: "API Key",
		manualTokenHelp: "Create a personal API key in Linear Settings > API.",
		authType: "oauth",
	},

	figma: {
		name: "figma",
		displayName: "Figma",
		description: "Connect Figma to access design files and components",
		brandColor: "#F24E1E",
		hasSelectResources: true,
		selectResourcesLabel: "Select Projects",
		hasManualToken: true,
		manualTokenPlaceholder: "figd_...",
		manualTokenLabel: "Personal Access Token",
		manualTokenHelp: "Generate a token in Figma > Settings > Account > Personal access tokens.",
		authType: "oauth",
	},

	github: {
		name: "github",
		displayName: "GitHub",
		description: "Connect your GitHub account to access repositories",
		brandColor: "#24292F",
		iconImage: "/providers/github.png",
		iconLetter: "GH",
		hasSelectResources: true,
		selectResourcesLabel: "Select Repositories",
		hasManualToken: true,
		manualTokenPlaceholder: "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
		manualTokenLabel: "Access Token",
		manualTokenHelp: "Enter your GitHub Access Token.",
		manualTokenHelpLinkText: "How to find?",
		manualTokenHelpLinkUrl: "https://waveassist.io/blog/how-to-get-your-github-token-for-gitzoid",
		validateToken: validateGitHubToken,
		authType: "oauth",
	},

	// ─── Forms & Surveys ────────────────────────────────────

	typeform: {
		name: "typeform",
		displayName: "Typeform",
		description: "Connect Typeform to access form submissions and responses",
		brandColor: "#262627",
		hasSelectResources: true,
		selectResourcesLabel: "Select Forms",
		hasManualToken: true,
		manualTokenPlaceholder: "tfp_...",
		manualTokenLabel: "Personal Access Token",
		manualTokenHelp: "Create a personal access token in your Typeform account settings.",
		authType: "oauth",
	},

	// ─── Analytics ──────────────────────────────────────────

	google_analytics: {
		name: "google_analytics",
		displayName: "Google Analytics",
		description: "Connect Google Analytics to access traffic and conversion data",
		brandColor: "#E37400",
		iconLetter: "GA",
		hasSelectResources: true,
		selectResourcesLabel: "Select Properties",
		hasManualToken: false,
		authType: "oauth",
	},

	mixpanel: {
		name: "mixpanel",
		displayName: "Mixpanel",
		description: "Connect Mixpanel to access product analytics and user events",
		brandColor: "#7856FF",
		hasSelectResources: false,
		hasManualToken: true,
		manualTokenPlaceholder: "Enter service account secret...",
		manualTokenLabel: "Service Account Secret",
		manualTokenHelp: "Create a service account in Mixpanel Project Settings > Service Accounts.",
		authType: "api_key",
	},

	// ─── Meetings ───────────────────────────────────────────

	fireflies: {
		name: "fireflies",
		displayName: "Fireflies.ai",
		description: "Connect Fireflies to access meeting transcripts",
		brandColor: "#7C3AED",
		iconLetter: "F",
		hasSelectResources: false,
		hasManualToken: true,
		manualTokenPlaceholder: "Enter API key...",
		manualTokenLabel: "API Key",
		manualTokenHelp: "Find your API key at app.fireflies.ai > Integrations > Fireflies API.",
		authType: "api_key",
	},

	// ─── Calendar ───────────────────────────────────────────

	google_calendar: {
		name: "google_calendar",
		displayName: "Google Calendar",
		description: "Connect Google Calendar to access events and schedules",
		brandColor: "#4285F4",
		iconLetter: "GC",
		hasSelectResources: true,
		selectResourcesLabel: "Select Calendars",
		hasManualToken: false,
		authType: "oauth",
	},
};
