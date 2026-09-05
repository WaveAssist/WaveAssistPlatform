// ============================================================
// Brand config — the single source of truth for whitelabeling.
// Two fixed brands only: waveassist (default) + gitzoid.
//
// The active brand is decided at BUILD TIME by VITE_BRAND
// (set per Netlify site). This is authoritative in production —
// a waveassist deployment can never be switched to gitzoid at
// runtime. For local development only, a ?brand= param (persisted
// to localStorage) can override, so both brands can be previewed
// from one dev server. With nothing set, the app renders exactly
// as before (default = waveassist).
//
// Colors live in CSS (design-system.css, keyed by
// :root[data-brand="..."]). Per each brand studio, the mark is a
// TYPESET wordmark, not an image: /waveassist (Volt Lime slash) and
// /gitzoid (Patrol Green slash), both in JetBrains Mono. `accent`
// here mirrors --color-primary for the few places JS needs the
// value directly. Keep the two in sync.
// ============================================================
import React from "react";

export type BrandId = "waveassist" | "gitzoid";

// Hosted MCP endpoint (WaveAgent) + plugin marketplace — shown in the Connect MCP panel.
export const MCP_URL = (import.meta.env.VITE_MCP_URL && String(import.meta.env.VITE_MCP_URL).trim()) || "https://mcp.waveassist.ai/mcp";
export const MCP_MARKETPLACE = "WaveAssist/WaveAgent";

export interface Brand {
	id: BrandId;
	name: string; // full wordmark label (lowercase), e.g. "waveassist"
	analyticsName: string;
	title: string; // browser tab title
	accent: string; // brand accent (mirrors --color-primary in CSS)
	markLabel: string; // collapsed-mark suffix after the slash ("" = bare slash)
	billingModel: "credits" | "trial"; // WaveAssist = credits (PAYG); GitZoid = trial → Pro
	showRunUsage: boolean; // show per-run LLM usage on the runs pages (WaveAssist only)
	scoped: boolean; // restrict the dashboard to a single template
	templateKey: string | null; // the template the "Add" button deploys
	catalogUrl: string | null; // assistant catalog (null when scoped)
	signup: string; // login sub-headline (tagline)
	gaMeasurementId: string; // per-brand GA4 property, so each brand's analytics stay separate
	posthogKey: string; // per-brand PostHog project, matching that brand's marketing site
	pricingUrl: string; // marketing pricing page for this brand
}

export const BRANDS: Record<BrandId, Brand> = {
	waveassist: {
		id: "waveassist",
		name: "waveassist",
		analyticsName: "WaveAssist",
		title: "WaveAssist",
		accent: "#D8FF00", // Volt Lime — mirrors --color-primary
		markLabel: "wa",
		billingModel: "credits",
		showRunUsage: true,
		scoped: false,
		templateKey: null,
		catalogUrl: "https://waveassist.ai/assistants",
		signup: "Run deterministic AI agents in the cloud.",
		gaMeasurementId: "G-RHQ9VZRVXH",
		posthogKey: import.meta.env.VITE_WAVEASSIST_POSTHOG_KEY || "", // shared with the WaveAssist marketing site
		pricingUrl: "https://waveassist.ai/pricing",
	},
	gitzoid: {
		id: "gitzoid",
		name: "gitzoid",
		analyticsName: "GitZoid",
		title: "GitZoid",
		accent: "#12C46A", // Patrol Green — mirrors --color-primary
		markLabel: "gz",
		billingModel: "trial",
		showRunUsage: false,
		scoped: true,
		templateKey: "gitzoid",
		catalogUrl: null,
		signup: "The product manager for your coding agents.",
		// GitZoidWebsite GA4 property (483777017) — same ID as the GitZoid marketing site,
		// so site + dashboard land in one property. NOT the Firebase auto-stream (G-9BBL3KD4DV).
		gaMeasurementId: "G-PX7J3JNWKP",
		// GitZoid marketing site's PostHog project, so GitZoid site + dashboard land together
		// (not the shared WaveAssist project the dashboard used before).
		posthogKey: import.meta.env.VITE_GITZOID_POSTHOG_KEY || "",
		pricingUrl: "https://gitzoid.com/pricing",
	},
};

const VALID_BRANDS = Object.keys(BRANDS) as BrandId[];

function isBrandId(value: string | null | undefined): value is BrandId {
	return !!value && (VALID_BRANDS as string[]).includes(value);
}

let _cached: Brand | null = null;

/** Resolve the active brand. Order:
 *  1. VITE_BRAND (build-time) — authoritative, used in production.
 *  2. ?brand= / localStorage — DEV ONLY, for local preview.
 *  3. Default: waveassist.
 *  Cached: the brand never changes within a session. */
function resolveBrand(): Brand {
	if (_cached) return _cached;

	const envBrand = String(import.meta.env.VITE_BRAND ?? "").toLowerCase();
	if (isBrandId(envBrand)) {
		_cached = BRANDS[envBrand];
		return _cached;
	}

	if (import.meta.env.DEV) {
		try {
			const stored = localStorage.getItem("brand");
			if (isBrandId(stored)) {
				_cached = BRANDS[stored];
				return _cached;
			}
		} catch {
			/* localStorage unavailable */
		}
	}

	_cached = BRANDS.waveassist;
	return _cached;
}

/** Capture ?brand= once at bootstrap (DEV ONLY). In production the
 *  brand is fixed by the build, so the param is ignored. */
export function captureBrandParam(): void {
	if (!import.meta.env.DEV) return;
	try {
		const param = new URLSearchParams(window.location.search).get("brand");
		if (isBrandId(param)) {
			localStorage.setItem("brand", param);
			_cached = null; // allow the fresh param to win
		}
	} catch {
		/* localStorage/URL unavailable: fall through to default */
	}
}

/** The active brand. Never changes within a session. Defaults to waveassist. */
export function getBrand(): Brand {
	return resolveBrand();
}

/** Stamp the document with the active brand: sets data-brand (drives the
 *  CSS token set), the tab title, and the favicon. Called once from main.tsx. */
export function applyBrandToDocument(): void {
	const brand = getBrand();
	try {
		document.documentElement.dataset.brand = brand.id;
		document.title = brand.title;
		// Favicon: the lone slash on a carbon tile, tinted with the brand accent.
		const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="${brand.id === "gitzoid" ? "#0B0E12" : "#0B0C0F"}"/><text x="50%" y="50%" dy="0.02em" text-anchor="middle" dominant-baseline="central" font-family="'JetBrains Mono',ui-monospace,monospace" font-weight="700" font-size="46" fill="${brand.accent}">/</text></svg>`;
		let link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
		if (!link) {
			link = document.createElement("link");
			link.rel = "icon";
			document.head.appendChild(link);
		}
		link.type = "image/svg+xml";
		link.href = `data:image/svg+xml,${encodeURIComponent(svg)}`;
	} catch {
		/* SSR / no document */
	}
}

interface BrandLogoProps {
	variant?: "full" | "mark";
	size?: number; // wordmark font-size (px)
	className?: string;
	style?: React.CSSProperties;
	alt?: string;
}

/** Renders the active brand's typeset wordmark: a brand-accent slash "/"
 *  followed by the brand name (full) or a short mark (collapsed). Both
 *  brands are typographic — no raster logos. */
export const BrandLogo: React.FC<BrandLogoProps> = ({ variant = "full", size, className, style, alt }) => {
	const brand = getBrand();
	const fontSize = size ?? 24;
	const label = variant === "mark" ? brand.markLabel : brand.name;
	return (
		<span
			className={className}
			aria-label={alt ?? brand.analyticsName}
			style={{
				fontFamily: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
				fontWeight: 600,
				fontSize: `${fontSize}px`,
				lineHeight: 1,
				letterSpacing: "-0.02em",
				color: "var(--color-text-primary)",
				whiteSpace: "nowrap",
				display: "inline-flex",
				alignItems: "center",
				userSelect: "none",
				...style,
			}}>
			<span style={{ color: "var(--color-primary)" }}>/</span>
			{label}
		</span>
	);
};
