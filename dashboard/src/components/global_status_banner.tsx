import React, { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { getBrand } from "../config/branding";
import { fetchBillingOverview } from "../services/all_projects_services";
import { fetchCreditsApi } from "../services/credits_services";
import "./global_status_banner.css";

// A persistent, brand-aware account-status bar shown across the app shell when the
// account can no longer run: GitZoid = trial exhausted (auto-paused), WaveAssist =
// zero credits. Copy differs by brand because the states differ. GitZoid genuinely
// pauses; WaveAssist is pay-as-you-go and resumes on top-up.

// Dismiss is intentionally in-memory (module-scoped), NOT persisted. Swiping the
// banner away clears it for the current session, but a fresh page load re-shows it
// while the underlying condition still holds, so it can't be permanently lost.
let sessionDismissed = false;

type BannerContent = { icon: string; message: string; ctaLabel: string };

const GlobalStatusBanner: React.FC = () => {
	const navigate = useNavigate();
	const location = useLocation();
	const [content, setContent] = useState<BannerContent | null>(null);
	const [dismissed, setDismissed] = useState(sessionDismissed);

	useEffect(() => {
		let cancelled = false;
		const uid = localStorage.getItem("uid");
		if (!uid) return;

		const resolve = async (): Promise<BannerContent | null> => {
			try {
				if (getBrand().billingModel === "trial") {
					// GitZoid: trial done and not yet on Pro → deployments are auto-paused.
					const billing = await fetchBillingOverview(uid);
					const sub = billing?.subscription;
					const isPro =
						billing?.account_plan_name === "gitzoid_pro" ||
						(!!sub && ["active", "trialing"].includes(sub.status));
					if (billing?.trial?.exhausted && !isPro) {
						return {
							icon: "bi-pause-circle-fill",
							message: "Free trial complete. GitZoid is paused until you upgrade.",
							ctaLabel: "Upgrade to Pro",
						};
					}
				} else {
					// WaveAssist: pay-as-you-go. Zero balance doesn't pause anything; runs just
					// can't afford paid LLM steps and resume seamlessly on top-up.
					const credits = await fetchCreditsApi();
					if ((credits?.limit_remaining ?? 0) <= 0) {
						return {
							icon: "bi-exclamation-circle-fill",
							message: "You're out of credits. Add credits to keep your assistants running.",
							ctaLabel: "Add credits",
						};
					}
				}
			} catch {
				/* status unknown, so show nothing rather than a misleading banner */
			}
			return null;
		};

		resolve().then((c) => {
			if (!cancelled) setContent(c);
		});
		return () => {
			cancelled = true;
		};
	}, []);

	// Hide while resolving/unmet, once dismissed, and on the billing page itself
	// (which already surfaces this state in-page, so a banner there is redundant).
	if (!content || dismissed || location.pathname === "/manage/credits") return null;

	const dismiss = () => {
		sessionDismissed = true;
		setDismissed(true);
	};

	return (
		<div className="global-status-banner" role="status">
			<i className={`bi ${content.icon}`}></i>
			<span className="global-status-banner-text">{content.message}</span>
			<button className="global-status-banner-cta" onClick={() => navigate("/manage/credits")}>
				{content.ctaLabel}
			</button>
			<button className="global-status-banner-dismiss" aria-label="Dismiss" onClick={dismiss}>
				<i className="bi bi-x-lg"></i>
			</button>
		</div>
	);
};

export default GlobalStatusBanner;
