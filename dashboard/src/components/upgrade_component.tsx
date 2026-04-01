import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Spinner } from "react-bootstrap";
import { usePostHog } from "posthog-js/react";
import { createCheckoutSession } from "../services/all_projects_services";
import { getStoredAccessPlan, getStoredDisplayPlan } from "../utils/plan";
import { refreshUserProfile } from "../services/login_services";
import { useToast } from "../utils/toast_context";
import { useDodoCheckout } from "../hooks/useDodoCheckout";
import { PLANS, PlanOption } from "../utils/plans";
import WALogo from "../assets/Logo/GreenLogo_Full_white_no_w.png";
import "./upgrade_component.css";

const UpgradeComponent: React.FC = () => {
	const location = useLocation();
	const navigate = useNavigate();
	const posthog = usePostHog();
	const { showToast } = useToast();
	const { openDodoCheckout } = useDodoCheckout();

	const params = new URLSearchParams(location.search);
	const planParam = params.get("plan")?.toLowerCase();
	const initialPlan = planParam === "plus" || planParam === "pro" ? planParam : "pro";

	const [selectedPlanKey, setSelectedPlanKey] = useState<string>(initialPlan);
	const [isPaymentLoading, setIsPaymentLoading] = useState(false);
	const [paymentSuccess, setPaymentSuccess] = useState(false);
	const [activatedPlanLabel, setActivatedPlanLabel] = useState("");

	const currentAccessPlan = getStoredAccessPlan();
	const isAlreadyPaid = currentAccessPlan === "plus" || currentAccessPlan === "pro";
	const currentDisplayPlan = getStoredDisplayPlan();

	useEffect(() => {
		try {
			posthog?.capture("$pageview", { page_category: "upgrade" });
		} catch (_) {}
	}, []);

	const pollForPlanUpdate = () => {
		setTimeout(async () => {
			await refreshUserProfile();
			const updated = getStoredAccessPlan();
			if (updated === "plus" || updated === "pro") {
				const label = updated.charAt(0).toUpperCase() + updated.slice(1);
				setActivatedPlanLabel(label);
				setPaymentSuccess(true);
			}
		}, 5000);

		setTimeout(async () => {
			await refreshUserProfile();
			const updated = getStoredAccessPlan();
			if (updated === "plus" || updated === "pro") {
				const label = updated.charAt(0).toUpperCase() + updated.slice(1);
				setActivatedPlanLabel(label);
				setPaymentSuccess(true);
			}
		}, 15000);
	};

	const handleSelectPlan = async (plan: PlanOption) => {
		const uid = localStorage.getItem("uid");
		if (!uid) {
			showToast("Please log in again.", "danger");
			return;
		}
		try {
			setIsPaymentLoading(true);
			setSelectedPlanKey(plan.key);
			const response = await createCheckoutSession(
				uid,
				"subscription",
				plan.price.toFixed(2),
				plan.credits.toFixed(2),
				plan.key
			);
			if (response.success !== "1" || !response?.data?.checkout_url) {
				throw new Error(response.message || "Could not create checkout");
			}
			try {
				posthog?.capture("payment_initiated", {
					type: "subscription",
					plan: plan.key,
					amount: plan.price,
					currency: "USD",
					source: "upgrade_page",
				});
			} catch (_) {}
			await openDodoCheckout(response.data.checkout_url, {
				onOpened: () => setIsPaymentLoading(false),
				onClosed: () => {
					setIsPaymentLoading(false);
					pollForPlanUpdate();
				},
				onError: () => setIsPaymentLoading(false),
			});
		} catch {
			showToast("Payment failed. Please try again.", "danger");
			setIsPaymentLoading(false);
		}
	};

	// ── Already on paid plan ──
	if (isAlreadyPaid) {
		return (
			<div className="upgrade-page">
				<div className="upgrade-page-header">
					<img src={WALogo} alt="WaveAssist" className="upgrade-logo" />
					<button className="upgrade-back-link" onClick={() => navigate("/manage")}>
						<i className="bi bi-arrow-left me-1"></i>Back to dashboard
					</button>
				</div>
				<div className="upgrade-already-paid">
					<div className="upgrade-already-icon">
						<i className="bi bi-patch-check-fill"></i>
					</div>
					<h2 className="upgrade-already-title">You're on {currentDisplayPlan}</h2>
					<p className="upgrade-already-desc">
						Your plan is already active. Head to the dashboard to manage your assistant or view billing.
					</p>
					<div className="upgrade-already-actions">
						<button className="upgrade-cta-btn primary" onClick={() => navigate("/manage")}>
							Go to Dashboard
						</button>
						<button className="upgrade-cta-btn secondary" onClick={() => navigate("/manage/credits")}>
							View Billing
						</button>
					</div>
				</div>
			</div>
		);
	}

	// ── Payment success ──
	if (paymentSuccess) {
		return (
			<div className="upgrade-page">
				<div className="upgrade-page-header">
					<img src={WALogo} alt="WaveAssist" className="upgrade-logo" />
				</div>
				<div className="upgrade-success">
					<div className="upgrade-success-icon">
						<i className="bi bi-check-circle-fill"></i>
					</div>
					<h2 className="upgrade-success-title">You're now on {activatedPlanLabel}!</h2>
					<p className="upgrade-success-desc">
						Your plan is active. Set up your first assistant to start running workflows.
					</p>
					<button className="upgrade-cta-btn primary" onClick={() => navigate("/manage")}>
						Set up your assistant
						<i className="bi bi-arrow-right ms-2"></i>
					</button>
					<button className="upgrade-cta-btn secondary mt-2" onClick={() => navigate("/manage/credits")}>
						View billing
					</button>
				</div>
			</div>
		);
	}

	// ── Plan selection ──
	return (
		<div className="upgrade-page">
			<div className="upgrade-page-header">
				<img src={WALogo} alt="WaveAssist" className="upgrade-logo" />
				<button className="upgrade-back-link" onClick={() => navigate("/manage")}>
					<i className="bi bi-arrow-left me-1"></i>Back to dashboard
				</button>
			</div>

			<div className="upgrade-page-body">
				<div className="upgrade-heading-section">
					<h1 className="upgrade-page-title">Choose your plan</h1>
					<p className="upgrade-page-subtitle">
						Unlock credits, unlimited runs, and premium support. Cancel anytime.
					</p>
				</div>

				<div className="upgrade-cards-grid">
					{PLANS.map((plan) => {
						const isSelected = selectedPlanKey === plan.key;
						return (
							<div
								key={plan.key}
								className={`upgrade-card ${plan.recommended ? "recommended" : ""} ${isSelected ? "selected" : ""}`}
								onClick={() => !isPaymentLoading && setSelectedPlanKey(plan.key)}>
								{plan.recommended && !planParam && <div className="upgrade-card-badge">Most Popular</div>}
								<h3 className="upgrade-card-name">{plan.label}</h3>
								<div className="upgrade-card-price">
									<span className="upgrade-price-amount">${plan.price}</span>
									<span className="upgrade-price-period">/month</span>
								</div>
								<ul className="upgrade-features-list">
									{plan.features.map((f, i) => (
										<li key={i}>
											<i className="bi bi-check-lg"></i>
											<span>{f}</span>
										</li>
									))}
								</ul>
								<button
									className={`upgrade-select-btn ${isSelected ? "primary" : "secondary"}`}
									onClick={(e) => {
										e.stopPropagation();
										handleSelectPlan(plan);
									}}
									disabled={isPaymentLoading}>
									{isPaymentLoading && selectedPlanKey === plan.key ? (
										<Spinner animation="border" size="sm" />
									) : (
										`Select ${plan.label}`
									)}
								</button>
							</div>
						);
					})}
				</div>

				<div className="upgrade-page-footer">
					<a
						href="https://waveassist.io/pricing"
						target="_blank"
						rel="noopener noreferrer"
						className="upgrade-pricing-link">
						<i className="bi bi-box-arrow-up-right me-1"></i>
						View full pricing & plan details
					</a>
				</div>
			</div>
		</div>
	);
};

export default UpgradeComponent;
