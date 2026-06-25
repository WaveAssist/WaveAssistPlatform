// ============================================================
// Brand config — the single source of truth for whitelabeling.
// Two fixed brands only: waveassist (default) + gitzoid.
// Active brand is chosen by a ?brand= param captured once at
// app bootstrap (see captureBrandParam, called from main.tsx)
// and persisted to localStorage. With no param the app renders
// exactly as before (default = waveassist).
// ============================================================
import React from "react";
import waveLogo from "../assets/Logo/GreenLogo_Full_white_no_w.png";
import waveMark from "../assets/Logo/Wave_Predict_W_Logo.png";

export type BrandId = "waveassist" | "gitzoid";

export interface Brand {
	id: BrandId;
	name: string;
	analyticsName: string;
	title: string; // browser tab title
	wordmark: boolean; // true -> render the /gitzoid type wordmark instead of an image
	accent: string; // brand accent (the slash, highlights)
	logoFull?: string; // image brands only
	logoMark?: string; // image brands only (collapsed)
	scoped: boolean; // restrict the dashboard to a single template
	templateKey: string | null; // the template the "Add" button deploys
	catalogUrl: string | null; // assistant catalog (null when scoped)
	welcome: string; // login headline
	signup: string; // login sub-headline
}

export const BRANDS: Record<BrandId, Brand> = {
	waveassist: {
		id: "waveassist",
		name: "WaveAssist",
		analyticsName: "WaveAssist",
		title: "WaveAssistDashboard",
		wordmark: false,
		accent: "#1ED66C",
		logoFull: waveLogo,
		logoMark: waveMark,
		scoped: false,
		templateKey: null,
		catalogUrl: "https://waveassist.ai/assistants",
		welcome: "Welcome to WaveAssist",
		signup: "Sign up for free to access your workflows",
	},
	gitzoid: {
		id: "gitzoid",
		name: "GitZoid",
		analyticsName: "GitZoid",
		title: "GitZoid Control Panel",
		wordmark: true,
		accent: "#12C46A", // Patrol Green
		scoped: true,
		templateKey: "gitzoid",
		catalogUrl: null,
		welcome: "Welcome to GitZoid",
		signup: "Reviews every PR, watches for risk, sums up your week.",
	},
};

const VALID_BRANDS = Object.keys(BRANDS) as BrandId[];

/** Capture ?brand= once at bootstrap, before React mounts. Persisting
 *  here (synchronously) means the choice survives the Firebase auth
 *  redirect, so no per-component param threading is needed. */
export function captureBrandParam(): void {
	try {
		const param = new URLSearchParams(window.location.search).get("brand");
		if (param && (VALID_BRANDS as string[]).includes(param)) {
			localStorage.setItem("brand", param);
		}
	} catch {
		/* localStorage/URL unavailable: fall through to default */
	}
}

/** The active brand. Never changes within a session, so a plain
 *  function (not a hook/context) is enough. Defaults to waveassist. */
export function getBrand(): Brand {
	try {
		const stored = localStorage.getItem("brand");
		if (stored && (VALID_BRANDS as string[]).includes(stored)) {
			return BRANDS[stored as BrandId];
		}
	} catch {
		/* ignore */
	}
	return BRANDS.waveassist;
}

interface BrandLogoProps {
	variant?: "full" | "mark";
	size?: number; // wordmark font-size (px); ignored by image brands
	className?: string;
	style?: React.CSSProperties;
	alt?: string;
}

/** Renders the active brand's mark. Image brands keep their existing
 *  <img> (and className-driven sizing) untouched. The gitzoid brand
 *  renders the /gitzoid type wordmark (JetBrains Mono, green slash). */
export const BrandLogo: React.FC<BrandLogoProps> = ({ variant = "full", size, className, style, alt }) => {
	const brand = getBrand();

	if (brand.wordmark) {
		const fontSize = size ?? 24;
		const label = variant === "mark" ? "gz" : brand.name.toLowerCase();
		return (
			<span
				className={className}
				aria-label={alt ?? brand.name}
				style={{
					fontFamily: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
					fontWeight: 600,
					fontSize: `${fontSize}px`,
					lineHeight: 1,
					letterSpacing: "-0.01em",
					color: "#FFFFFF",
					whiteSpace: "nowrap",
					display: "inline-flex",
					alignItems: "center",
					userSelect: "none",
					...style,
				}}>
				<span style={{ color: brand.accent }}>/</span>
				{label}
			</span>
		);
	}

	return <img src={variant === "mark" ? brand.logoMark : brand.logoFull} alt={alt ?? brand.name} className={className} style={style} />;
};
