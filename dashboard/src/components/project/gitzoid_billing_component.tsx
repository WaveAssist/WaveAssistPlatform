import React, { useEffect, useState } from "react";
import { Spinner } from "react-bootstrap";
import { fetchBillingOverview, createCheckoutSession, createBillingPortalSession } from "../../services/all_projects_services";
import { refreshUserProfile } from "../../services/login_services";
import { useToast } from "../../utils/toast_context";
import { useRefresh } from "../../utils/RefreshContext";
import { useDodoCheckout } from "../../hooks/useDodoCheckout";
import "./credits_component.css";

// GitZoid billing: a free trial (shown as friendly capabilities over one usage bar) that
// converts to a single flat plan — GitZoid Pro. No credits, no packages.

const GITZOID_PRO_PRICE = 19; // gitzoid_pro price_usd (backend VALID_UPGRADE_PLANS) — flat monthly
const mono = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace";

const CAPABILITIES = [
	{ label: "Pull-request reviews", note: "included · ~10" },
	{ label: "Weekly digest", note: "included · ~1" },
	{ label: "Security scan", note: "included · ~1" },
];
const PRO_FEATURES = ["Unlimited PR reviews, digests & scans", "Up to 50 repos", "No per-seat pricing, no credits, no overage", "Works inside GitHub — no new tool to learn"];

interface Trial { on_trial: boolean; used: number; limit: number; remaining: number; exhausted: boolean }
interface Billing {
	account_plan_name: string;
	product: string;
	trial: Trial;
	subscription: { plan_name: string; status: string; current_period_end?: string } | null;
	payments?: Array<{ amount?: string; currency?: string; status?: string; created_at?: string; invoice_url?: string }>;
}

const eyebrow: React.CSSProperties = { fontFamily: mono, fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--color-text-secondary)" };
const card: React.CSSProperties = { background: "var(--color-bg-card)", border: "1px solid var(--color-border)", borderRadius: 12, padding: 24, color: "var(--color-text-primary)", height: "100%" };
const primaryBtn: React.CSSProperties = { background: "var(--color-primary)", color: "var(--color-text-button)", border: "none", borderRadius: 8, padding: "11px 16px", fontWeight: 600, width: "100%", cursor: "pointer" };

const GitZoidBillingComponent: React.FC = () => {
	const { showToast } = useToast();
	const { shouldRefresh } = useRefresh();
	const { openDodoCheckout } = useDodoCheckout();
	const [billing, setBilling] = useState<Billing | null>(null);
	const [loading, setLoading] = useState(true);
	const [paying, setPaying] = useState(false);

	const load = async () => {
		const uid = localStorage.getItem("uid");
		if (!uid) return;
		try {
			setBilling(await fetchBillingOverview(uid));
		} catch {
			showToast("Failed to load billing.", "warning");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => { load(); }, [shouldRefresh]);

	const handleUpgrade = async () => {
		const uid = localStorage.getItem("uid");
		if (!uid) return showToast("Please log in again.", "danger");
		try {
			setPaying(true);
			const res = await createCheckoutSession(uid, "subscription", GITZOID_PRO_PRICE.toFixed(2), "25", "gitzoid_pro");
			if (res.success !== "1" || !res?.data?.checkout_url) throw new Error(res.message || "Checkout failed");
			await openDodoCheckout(res.data.checkout_url, {
				onOpened: () => setPaying(false),
				onClosed: () => { setPaying(false); setTimeout(async () => { await refreshUserProfile(); await load(); }, 12000); },
				onError: () => setPaying(false),
			});
		} catch {
			showToast("Could not start checkout.", "danger");
			setPaying(false);
		}
	};

	const handlePortal = async () => {
		const uid = localStorage.getItem("uid");
		if (!uid) return;
		try {
			const data = await createBillingPortalSession(uid);
			if (data?.portal_url) window.open(data.portal_url, "_blank", "noopener,noreferrer");
		} catch {
			showToast("Unable to open billing portal.", "danger");
		}
	};

	if (loading) {
		return (
			<div className="main-container">
				<div className="d-flex justify-content-center align-items-center" style={{ height: 240 }}>
					<Spinner animation="border" role="status" style={{ color: "var(--color-primary)" }} />
				</div>
			</div>
		);
	}

	const trial = billing?.trial;
	const sub = billing?.subscription;
	const isPro = billing?.account_plan_name === "gitzoid_pro" || (!!sub && ["active", "trialing"].includes(sub.status));
	const used = trial?.used ?? 0;
	const limit = trial?.limit ?? 30;
	const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
	const exhausted = !!trial?.exhausted;
	// Billing history shows only successful charges — pending/failed checkouts are abandoned attempts, not history.
	const paidHistory = (billing?.payments || []).filter((p) => p.status === "succeeded" || p.status === "completed");

	return (
		<div className="main-container credits-container">
			<div className="mt-3 d-flex flex-column">
				<div className="credits-header">
					<div className="credits-header-left">
						<h3 className="credits-title">Billing</h3>
						<span className="plan-badge plan-badge-free"><i className="bi bi-lightning-charge-fill"></i>{isPro ? "GitZoid Pro" : "Free trial"}</span>
					</div>
				</div>

				{isPro ? (
					<>
						<div className="row">
							{/* Subscription status */}
							<div className="col-md-6 mb-3">
								<div style={card}>
									<div style={{ ...eyebrow, color: "var(--color-primary)" }}>GitZoid Pro</div>
									<div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8 }}>
										<i className="bi bi-check-circle-fill text-success" style={{ fontSize: "1.4rem" }}></i>
										<span style={{ fontSize: 18, fontWeight: 600 }}>Active</span>
									</div>
									<div style={{ display: "flex", alignItems: "baseline", gap: 6, margin: "16px 0 2px" }}>
										<span style={{ fontSize: 30, fontWeight: 700 }}>${GITZOID_PRO_PRICE}</span>
										<span style={{ color: "var(--color-text-secondary)" }}>/month</span>
									</div>
									<div style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
										{sub?.current_period_end ? `Renews on ${new Date(sub.current_period_end).toLocaleDateString()}` : "flat · cancel anytime"}
									</div>
									<button style={{ ...primaryBtn, background: "transparent", color: "var(--color-text-primary)", border: "1px solid var(--color-border)", marginTop: 18 }} onClick={handlePortal}>Manage billing</button>
								</div>
							</div>
							{/* What's included */}
							<div className="col-md-6 mb-3">
								<div style={card}>
									<div style={eyebrow}>What's included</div>
									<ul style={{ listStyle: "none", padding: 0, margin: "14px 0 0" }}>
										{PRO_FEATURES.map((f) => (
											<li key={f} style={{ display: "flex", gap: 8, alignItems: "flex-start", padding: "8px 0", color: "var(--color-text-primary)" }}><i className="bi bi-check-lg text-success"></i>{f}</li>
										))}
									</ul>
								</div>
							</div>
						</div>

						{/* Billing history */}
						<div style={{ ...card, height: "auto", marginTop: 4 }}>
							<div style={eyebrow}>Billing history</div>
							{paidHistory.length > 0 ? (
								<div style={{ marginTop: 14 }}>
									{paidHistory.slice(0, 8).map((p, i, arr) => {
										return (
											<div key={i} style={{ display: "flex", alignItems: "center", gap: 16, padding: "13px 0", borderBottom: i < arr.length - 1 ? "1px solid var(--color-border)" : "none" }}>
												<span style={{ color: "var(--color-text-secondary)", fontSize: 13, flex: 1 }}>
													{p.created_at ? new Date(p.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "—"}
												</span>
												<span style={{ fontFamily: mono, fontSize: 14, fontWeight: 600 }}>
													${p.amount}
													<span style={{ color: "var(--color-text-secondary)", fontWeight: 400, marginLeft: 4, fontSize: 11 }}>{p.currency || "USD"}</span>
												</span>
												<span style={{
													fontFamily: mono, fontSize: 11, letterSpacing: "0.05em", textTransform: "uppercase", padding: "4px 11px", borderRadius: 100, minWidth: 96, textAlign: "center",
													color: "var(--color-primary)",
													background: "rgba(var(--color-primary-rgb),0.12)",
													border: "1px solid rgba(var(--color-primary-rgb),0.30)",
												}}>{p.status}</span>
												{p.invoice_url ? (
													<a
														href={p.invoice_url}
														target="_blank"
														rel="noopener noreferrer"
														onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--color-primary)"; e.currentTarget.style.color = "var(--color-primary)"; }}
														onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--color-border)"; e.currentTarget.style.color = "var(--color-text-primary)"; }}
														style={{ fontSize: 12, padding: "5px 14px", borderRadius: 8, border: "1px solid var(--color-border)", color: "var(--color-text-primary)", textDecoration: "none", whiteSpace: "nowrap", transition: "all 0.15s ease" }}>
														View invoice
													</a>
												) : (
													<span style={{ display: "inline-block", width: 92 }} />
												)}
											</div>
										);
									})}
								</div>
							) : (
								<p style={{ color: "var(--color-text-secondary)", fontSize: 13, marginTop: 12, marginBottom: 0 }}>No payments yet.</p>
							)}
						</div>
					</>
				) : (
					<div className="row">
						{/* Left — current trial status */}
						<div className="col-md-6 mb-3">
							<div style={card}>
								<div style={eyebrow}>{exhausted ? "Free trial · complete" : "Your free trial"}</div>
								<div style={{ height: 8, background: "var(--color-bg-section)", borderRadius: 100, overflow: "hidden", margin: "16px 0 6px" }}>
									<div style={{ height: "100%", width: `${pct}%`, background: "var(--color-primary)", borderRadius: 100 }} />
								</div>
								<div style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
									{exhausted ? "Trial complete — runs are paused until you upgrade." : `Trial usage · ${pct}% used`}
								</div>
								<div style={{ margin: "18px 0 0" }}>
									{CAPABILITIES.map((c) => (
										<div key={c.label} style={{ display: "flex", justifyContent: "space-between", padding: "9px 0", borderBottom: "1px solid var(--color-border)" }}>
											<span>{c.label}</span>
											<span style={{ fontFamily: mono, color: "var(--color-text-secondary)", fontSize: 13 }}>{c.note}</span>
										</div>
									))}
								</div>
								<p style={{ color: "var(--color-text-secondary)", fontSize: 12.5, margin: "16px 0 0" }}>First 10 outputs free — no card required.</p>
							</div>
						</div>

						{/* Right — the Pro offer */}
						<div className="col-md-6 mb-3">
							<div style={{ ...card, borderColor: "var(--color-primary)" }}>
								<div style={{ ...eyebrow, color: "var(--color-primary)" }}>GitZoid Pro</div>
								<div style={{ display: "flex", alignItems: "baseline", gap: 6, margin: "10px 0 2px" }}>
									<span style={{ fontSize: 34, fontWeight: 700 }}>${GITZOID_PRO_PRICE}</span>
									<span style={{ color: "var(--color-text-secondary)" }}>/month</span>
								</div>
								<div style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>flat · cancel anytime</div>
								<ul style={{ listStyle: "none", padding: 0, margin: "16px 0" }}>
									{PRO_FEATURES.map((f) => (
										<li key={f} style={{ display: "flex", gap: 8, alignItems: "flex-start", padding: "6px 0", color: "var(--color-text-primary)" }}><i className="bi bi-check-lg text-success"></i>{f}</li>
									))}
								</ul>
								<button style={primaryBtn} onClick={handleUpgrade} disabled={paying}>
									{paying ? <Spinner animation="border" size="sm" /> : exhausted ? "Upgrade to continue" : "Upgrade to GitZoid Pro"}
								</button>
							</div>
						</div>
					</div>
				)}
			</div>
		</div>
	);
};

export default GitZoidBillingComponent;
