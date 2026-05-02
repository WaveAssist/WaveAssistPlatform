import React, { useEffect, useState } from "react";
import { usePostHog } from "posthog-js/react";
import { useLocation, useNavigate } from "react-router-dom";
import { Modal, Spinner } from "react-bootstrap";
import { fetchCreditsApi } from "../../services/credits_services";
import { createBillingPortalSession, createCheckoutSession, fetchBillingOverview } from "../../services/all_projects_services";
import { refreshUserProfile } from "../../services/login_services";
import { useToast } from "../../utils/toast_context";
import { useRefresh } from "../../utils/RefreshContext";
import { getStoredDisplayPlan, persistUserPlan } from "../../utils/plan";
import { useDodoCheckout } from "../../hooks/useDodoCheckout";
import { PLANS } from "../../utils/plans";
import "./project_components.css";
import "./credits_component.css";

interface CreditsData {
	limit: number;
	usage: number;
	limit_remaining: number;
}

interface BillingOverview {
	account_plan_name: string;
	subscription: { plan_name: string; status: string; external_customer_id?: string } | null;
	payments: Array<{
		id: number;
		amount: string;
		currency: string;
		status: string;
		payment_type: string;
		created_at?: string;
		invoice_url?: string;
		external_customer_id?: string;
	}>;
}

const PAID_DISPLAY_PLANS = ["PLUS", "PRO"];
const SERVICE_FEE_RATE = 0.18;

const CreditsDodoComponent: React.FC = () => {
	const location = useLocation();
	const navigate = useNavigate();
	const [currentPlan, setCurrentPlan] = useState(getStoredDisplayPlan());
	const [creditsData, setCreditsData] = useState<CreditsData | null>(null);
	const [, setBillingOverview] = useState<BillingOverview | null>(null);
	const [loading, setLoading] = useState(true);
	const [showUpgradeModal, setShowUpgradeModal] = useState(false);
	const [showPurchaseModal, setShowPurchaseModal] = useState(false);
	const [purchaseAmount, setPurchaseAmount] = useState(10);
	const [isCustomSelected, setIsCustomSelected] = useState(false);
	const [isPaymentLoading, setIsPaymentLoading] = useState(false);
	const [isBillingLoading, setIsBillingLoading] = useState(false);
	const [hasBillingCustomer, setHasBillingCustomer] = useState(false);
	const [showCheckoutBanner, setShowCheckoutBanner] = useState(false);

	const { showToast } = useToast();
	const { shouldRefresh } = useRefresh();
	const posthog = usePostHog();
	const { openDodoCheckout } = useDodoCheckout();
	// Always drive UI from normalized account plan set during login parsing.
	const isPaidPlan = PAID_DISPLAY_PLANS.includes(currentPlan);

	const fetchCredits = async () => {
		const data = await fetchCreditsApi();
		setCreditsData(data);
	};

	const fetchBillingData = async () => {
		const uid = localStorage.getItem("uid");
		if (!uid) return;
		const data = await fetchBillingOverview(uid);
		setBillingOverview(data);
		if (data?.account_plan_name) {
			const { displayPlan } = persistUserPlan(data.account_plan_name);
			setCurrentPlan(displayPlan);
		} else {
			setCurrentPlan(getStoredDisplayPlan());
		}
		// Determine if user has a Dodo customer ID (same logic as backend create_portal_session)
		const subCustomer = data?.subscription?.external_customer_id;
		const payCustomer = data?.payments?.find((p: { external_customer_id?: string }) => p.external_customer_id)?.external_customer_id;
		setHasBillingCustomer(!!(subCustomer || payCustomer));
	};

	const refreshBillingState = async (showSpinner = false) => {
		try {
			if (showSpinner) setLoading(true);
			await Promise.all([fetchCredits(), fetchBillingData()]);
		} catch {
			showToast("Failed to load billing details.", "warning");
		} finally {
			setLoading(false);
		}
	};

	const startCheckout = async (opts: { useCase: "credits" | "subscription"; amount: number; credits: number; planName?: string }) => {
		const uid = localStorage.getItem("uid");
		if (!uid) return showToast("Please log in again.", "danger");
		try {
			setIsPaymentLoading(true);
			const response = await createCheckoutSession(uid, opts.useCase, opts.amount.toFixed(2), opts.credits.toFixed(2), opts.planName);
			if (response.success !== "1" || !response?.data?.checkout_url) {
				throw new Error(response.message || "Could not create checkout");
			}
			try {
				posthog?.capture("payment_initiated", { type: opts.useCase, plan: opts.planName, amount: opts.amount, currency: "USD" });
			} catch (_err) {}
			await openDodoCheckout(response.data.checkout_url, {
				onOpened: () => setIsPaymentLoading(false),
				onClosed: () => {
					setIsPaymentLoading(false);
					setTimeout(() => refreshBillingState(), 5000);
					setTimeout(async () => {
						await refreshUserProfile();
						await refreshBillingState();
					}, 15000);
				},
				onError: () => setIsPaymentLoading(false),
			});
		} catch {
			showToast("Payment failed. Please try again.", "danger");
			setIsPaymentLoading(false);
		}
	};

	const handleOpenBillingPortal = async () => {
		const uid = localStorage.getItem("uid");
		if (!uid) return showToast("Please log in again.", "danger");
		try {
			setIsBillingLoading(true);
			const data = await createBillingPortalSession(uid);
			if (!data?.portal_url) throw new Error("No portal URL");
			window.open(data.portal_url, "_blank", "noopener,noreferrer");
		} catch {
			showToast("Unable to open billing portal.", "danger");
		} finally {
			setIsBillingLoading(false);
		}
	};

	useEffect(() => {
		refreshBillingState(true);
	}, [shouldRefresh]);

	useEffect(() => {
		try {
			posthog?.capture("$pageview", { page_category: "credits" });
		} catch (_err) {}
	}, []);

	useEffect(() => {
		const params = new URLSearchParams(location.search);
		if (params.get("upgrade") === "true" && !isPaidPlan && !loading) {
			setShowUpgradeModal(true);
			navigate(location.pathname, { replace: true });
		}
		// Detect return from Dodo checkout
		if (params.get("checkout") === "complete" && params.get("status") === "succeeded") {
			setShowCheckoutBanner(true);
			navigate(location.pathname, { replace: true });
			setTimeout(() => refreshBillingState(), 5000);
			setTimeout(async () => {
				await refreshUserProfile();
				await refreshBillingState();
			}, 15000);
		}
	}, [location.search, isPaidPlan, loading]);

	const serviceFee = purchaseAmount * SERVICE_FEE_RATE;
	const creditTotal = purchaseAmount + serviceFee;
	const subscriptionSummary = currentPlan;

	if (loading) {
		return (
			<div className="main-container">
				<div className="d-flex justify-content-center align-items-center" style={{ height: 240 }}>
					<Spinner animation="border" role="status" variant="success" />
				</div>
			</div>
		);
	}

	return (
		<div className="main-container credits-container">
			<div className="mt-3 d-flex flex-column">
				{showCheckoutBanner && (
					<div className="checkout-success-banner">
						<i className="bi bi-check-circle-fill"></i>
						<span>Payment successful! Your credits may take a moment to reflect here.</span>
						<button className="checkout-banner-dismiss" onClick={() => setShowCheckoutBanner(false)}>
							<i className="bi bi-x-lg"></i>
						</button>
					</div>
				)}

				<div className="credits-header">
					<div className="credits-header-left">
						<h3 className="credits-title">Billing</h3>
						<span className={`plan-badge ${isPaidPlan ? "plan-badge-paid" : "plan-badge-free"}`}>
							<i className={`bi ${isPaidPlan ? "bi-patch-check-fill" : "bi-person-fill"}`}></i>
							{currentPlan}
						</span>
					</div>
					<button className="refresh-btn" onClick={() => refreshBillingState()} title="Refresh">
						<i className="bi bi-arrow-clockwise"></i>
					</button>
				</div>

				<div className="row">
					<div className="col-md-6">
						<div className="available-credits-card">
							<div className="text-center mb-2">
								<h1 className="credit-balance-amount">$ {creditsData?.limit_remaining?.toFixed(2) || "0.00"}</h1>
								<p className="credit-balance-label">Available Credits</p>
							</div>
							{creditsData != null && (
								<div className="credit-details">
									<div className="credit-detail-row">
										<span className="credit-detail-label">Total Credits</span>
										<span className="credit-detail-value">$ {(creditsData.limit ?? 0).toFixed(2)}</span>
									</div>
									<div className="credit-detail-row">
										<span className="credit-detail-label">Used</span>
										<span className="credit-detail-value used">$ {(creditsData.usage ?? 0).toFixed(2)}</span>
									</div>
								</div>
							)}
						</div>
					</div>

					<div className="col-md-6">
						{isPaidPlan ? (
							<div className="buy-credits-card">
								<div className="buy-credits-header"><h5 className="buy-credits-title">Add Credits</h5></div>
								<div className="buy-credits-content">
									<div className="credit-amount-section">
										<label className="form-label">Select Amount</label>
										<div className="credit-amount-buttons">
											{[5, 10, 20].map((amt) => (
												<button key={amt} className={`credit-amount-btn ${!isCustomSelected && purchaseAmount === amt ? "active" : ""}`} onClick={() => { setPurchaseAmount(amt); setIsCustomSelected(false); }}>
													${amt}
												</button>
											))}
											<div className={`custom-amount-input ${isCustomSelected ? "active" : ""}`} onClick={() => setIsCustomSelected(true)}>
												{(isCustomSelected || ![5, 10, 20].includes(purchaseAmount)) && <span className="dollar-sign">$</span>}
												<input
													type="text"
													placeholder="Custom"
													value={![5, 10, 20].includes(purchaseAmount) ? String(purchaseAmount) : ""}
													onChange={(e) => {
														const parsed = Number(e.target.value.trim().replace(/[^0-9.]/g, ""));
														if (!isNaN(parsed) && parsed > 0) setPurchaseAmount(parsed);
													}}
													onFocus={() => setIsCustomSelected(true)}
													onBlur={() => setIsCustomSelected(false)}
												/>
											</div>
										</div>
									</div>
									<div className="add-credits-section"><button className="add-credits-button" onClick={() => setShowPurchaseModal(true)}>Add Credits</button></div>
								</div>
							</div>
						) : (
							<div className="upgrade-plan-card">
								<div className="upgrade-card-icon"><i className="bi bi-rocket-takeoff-fill"></i></div>
								<h5 className="upgrade-card-title">Upgrade Your Plan</h5>
								<p className="upgrade-card-desc">Switch to Pro or Plus to purchase credits and unlock premium features.</p>
								<button className="upgrade-card-btn" onClick={() => setShowUpgradeModal(true)}>View Plans</button>
							</div>
						)}
					</div>
				</div>

				<div className="buy-credits-card mt-3 subscription-billing-row">
					<div className="subscription-billing-left">
						<h5 className="buy-credits-title subscription-billing-title">Subscription & Billing</h5>
						<span className="subscription-billing-status">{subscriptionSummary}</span>
					</div>
					<div className="manage-billing-wrapper">
						<button className="manage-billing-btn" onClick={handleOpenBillingPortal} disabled={isBillingLoading || !hasBillingCustomer}>{isBillingLoading ? "Opening..." : "Manage Billing"}</button>
						{!hasBillingCustomer && <span className="manage-billing-hint">Available after your first purchase</span>}
					</div>
				</div>
			</div>

			<Modal show={showUpgradeModal} onHide={() => setShowUpgradeModal(false)} size="lg" centered className="upgrade-modal">
				<Modal.Header closeButton>
					<div>
						<Modal.Title className="upgrade-modal-title">Upgrade Your Plan</Modal.Title>
						<p className="upgrade-modal-subtitle">Choose the plan that fits your needs</p>
					</div>
				</Modal.Header>
				<Modal.Body>
					<div className="upgrade-plans-grid">
						{PLANS.map((plan) => (
							<div key={plan.key} className={`upgrade-plan-option ${plan.recommended ? "recommended" : ""}`}>
								{plan.recommended && <div className="recommended-badge">Most Popular</div>}
								<h4 className="plan-option-name">{plan.label}</h4>
								<div className="plan-option-price"><span className="plan-price-amount">{`$${plan.price}`}</span><span className="plan-price-period">/month</span></div>
								<ul className="plan-features-list">{plan.features.map((f, i) => <li key={i}><i className="bi bi-check-lg"></i><span>{f}</span></li>)}</ul>
								<button className={`plan-select-btn ${plan.recommended ? "primary" : "secondary"}`} onClick={() => startCheckout({ useCase: "subscription", amount: plan.price, credits: plan.credits, planName: plan.key })} disabled={isPaymentLoading}>
									{isPaymentLoading ? <Spinner animation="border" size="sm" /> : `Select ${plan.label}`}
								</button>
							</div>
						))}
					</div>
					<div className="upgrade-footer">
						<a href="https://waveassist.ai/pricing" target="_blank" rel="noopener noreferrer" className="upgrade-pricing-link">
							<i className="bi bi-box-arrow-up-right"></i>
							View full pricing & plan details
						</a>
					</div>
				</Modal.Body>
			</Modal>

			<Modal show={showPurchaseModal} onHide={() => setShowPurchaseModal(false)} size="lg" centered>
				<Modal.Header closeButton><Modal.Title>Purchase Credits</Modal.Title></Modal.Header>
				<Modal.Body>
					<div className="purchase-modal-content">
						<div className="purchase-summary">
							<div className="summary-row"><span>Credits</span><span>${purchaseAmount}</span></div>
							<div className="summary-row"><span>Platform, Gateway & Taxes</span><span>${serviceFee.toFixed(2)}</span></div>
							<div className="summary-row total-row"><span>Total</span><div className="total-amount-container"><span className="total-amount">${creditTotal.toFixed(2)}</span></div></div>
						</div>
					</div>
					<div className="payment-buttons-row">
						<button className="payment-btn" onClick={() => startCheckout({ useCase: "credits", amount: Number(creditTotal.toFixed(2)), credits: purchaseAmount })} disabled={isPaymentLoading}>
							<span className="payment-btn-content">
								{isPaymentLoading ? (
									<>
										<Spinner animation="border" size="sm" className="me-2" />
										<span>Processing...</span>
									</>
								) : (
									<span>Pay Now</span>
								)}
							</span>
						</button>
					</div>
				</Modal.Body>
			</Modal>
		</div>
	);
};

export default CreditsDodoComponent;
