import React, { useEffect, useState } from "react";
import { usePostHog } from "posthog-js/react";
import { useLocation, useNavigate } from "react-router-dom";
import { Modal, Spinner } from "react-bootstrap";
import { fetchCreditsApi } from "../../services/credits_services";
import { createCheckoutSession } from "../../services/all_projects_services";
import { refreshUserProfile } from "../../services/login_services";
import { useToast } from "../../utils/toast_context";
import { useRefresh } from "../../utils/RefreshContext";
import { useDodoCheckout } from "../../hooks/useDodoCheckout";
import ConnectMcpPanel from "../ConnectMcpPanel";
import "./project_components.css";
import "./credits_component.css";

// WaveAssist billing is pure pay-as-you-go: a credit balance + "Add credits".
// No plans, no subscription, no manage-billing — just top up and connect over MCP.

interface CreditsData {
	limit: number;
	usage: number;
	limit_remaining: number;
}

const AMOUNTS = [5, 10, 15];
const SERVICE_FEE_RATE = 0.18;

const WaveAssistCreditsComponent: React.FC = () => {
	const location = useLocation();
	const navigate = useNavigate();
	const [creditsData, setCreditsData] = useState<CreditsData | null>(null);
	const [loading, setLoading] = useState(true);
	const [purchaseAmount, setPurchaseAmount] = useState(10);
	const [isCustomSelected, setIsCustomSelected] = useState(false);
	const [isPaymentLoading, setIsPaymentLoading] = useState(false);
	const [showPurchaseModal, setShowPurchaseModal] = useState(false);
	const [showMcpPanel, setShowMcpPanel] = useState(false);
	const [showCheckoutBanner, setShowCheckoutBanner] = useState(false);

	const { showToast } = useToast();
	const { shouldRefresh } = useRefresh();
	const posthog = usePostHog();
	const { openDodoCheckout } = useDodoCheckout();

	const refresh = async (showSpinner = false) => {
		try {
			if (showSpinner) setLoading(true);
			setCreditsData(await fetchCreditsApi());
		} catch {
			showToast("Failed to load credits.", "warning");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		refresh(true);
	}, [shouldRefresh]);

	useEffect(() => {
		try {
			posthog?.capture("$pageview", { page_category: "credits" });
		} catch (_err) {}
	}, []);

	useEffect(() => {
		const params = new URLSearchParams(location.search);
		if (params.get("checkout") === "complete" && params.get("status") === "succeeded") {
			setShowCheckoutBanner(true);
			navigate(location.pathname, { replace: true });
			setTimeout(() => refresh(), 5000);
			setTimeout(async () => {
				await refreshUserProfile();
				await refresh();
			}, 15000);
		}
	}, [location.search]);

	const startCheckout = async () => {
		const uid = localStorage.getItem("uid");
		if (!uid) return showToast("Please log in again.", "danger");
		try {
			setIsPaymentLoading(true);
			const total = Number((purchaseAmount * (1 + SERVICE_FEE_RATE)).toFixed(2));
			const response = await createCheckoutSession(uid, "credits", total.toFixed(2), purchaseAmount.toFixed(2));
			if (response.success !== "1" || !response?.data?.checkout_url) throw new Error(response.message || "Could not create checkout");
			try {
				posthog?.capture("payment_initiated", { type: "credits", amount: purchaseAmount, currency: "USD" });
			} catch (_err) {}
			await openDodoCheckout(response.data.checkout_url, {
				onOpened: () => setIsPaymentLoading(false),
				onClosed: () => {
					setIsPaymentLoading(false);
					setShowPurchaseModal(false);
					setTimeout(() => refresh(), 5000);
					setTimeout(async () => { await refreshUserProfile(); await refresh(); }, 15000);
				},
				onError: () => setIsPaymentLoading(false),
			});
		} catch {
			showToast("Payment failed. Please try again.", "danger");
			setIsPaymentLoading(false);
		}
	};

	const serviceFee = purchaseAmount * SERVICE_FEE_RATE;
	const creditTotal = purchaseAmount + serviceFee;

	if (loading) {
		return (
			<div className="main-container">
				<div className="d-flex justify-content-center align-items-center" style={{ height: 240 }}>
					<Spinner animation="border" role="status" style={{ color: "var(--color-primary)" }} />
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
						<button className="checkout-banner-dismiss" onClick={() => setShowCheckoutBanner(false)}><i className="bi bi-x-lg"></i></button>
					</div>
				)}

				<div className="credits-header">
					<div className="credits-header-left">
						<h3 className="credits-title">Billing</h3>
						<span className="plan-badge plan-badge-free"><i className="bi bi-lightning-charge-fill"></i>Pay as you go</span>
					</div>
					<button className="refresh-btn" onClick={() => refresh()} title="Refresh"><i className="bi bi-arrow-clockwise"></i></button>
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
						<div className="buy-credits-card">
							<div className="buy-credits-header"><h5 className="buy-credits-title">Add Credits</h5></div>
							<div className="buy-credits-content">
								<div className="credit-amount-section">
									<label className="form-label">Select Amount</label>
									<div className="credit-amount-buttons">
										{AMOUNTS.map((amt) => (
											<button key={amt} className={`credit-amount-btn ${!isCustomSelected && purchaseAmount === amt ? "active" : ""}`} onClick={() => { setPurchaseAmount(amt); setIsCustomSelected(false); }}>
												${amt}
											</button>
										))}
										<div className={`custom-amount-input ${isCustomSelected ? "active" : ""}`} onClick={() => setIsCustomSelected(true)}>
											{(isCustomSelected || !AMOUNTS.includes(purchaseAmount)) && <span className="dollar-sign">$</span>}
											<input
												type="text"
												placeholder="Custom"
												value={!AMOUNTS.includes(purchaseAmount) ? String(purchaseAmount) : ""}
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
					</div>
				</div>

				<div className="buy-credits-card mt-3 subscription-billing-row">
					<div className="subscription-billing-left">
						<h5 className="buy-credits-title subscription-billing-title">Connect over MCP</h5>
						<span className="subscription-billing-status">Build assistants from your editor: Claude Code, Cursor, and more.</span>
					</div>
					<div className="manage-billing-wrapper">
						<button className="manage-billing-btn" onClick={() => setShowMcpPanel(true)}>Connect MCP</button>
					</div>
				</div>
			</div>

			<ConnectMcpPanel show={showMcpPanel} onHide={() => setShowMcpPanel(false)} />

			<Modal show={showPurchaseModal} onHide={() => setShowPurchaseModal(false)} size="lg" centered>
				<Modal.Header closeButton><Modal.Title>Purchase Credits</Modal.Title></Modal.Header>
				<Modal.Body>
					<div className="purchase-modal-content">
						<div className="purchase-summary">
							<div className="summary-row"><span>Credits</span><span>${purchaseAmount}</span></div>
							<div className="summary-row"><span>Platform, Gateway &amp; Taxes</span><span>${serviceFee.toFixed(2)}</span></div>
							<div className="summary-row total-row"><span>Total</span><div className="total-amount-container"><span className="total-amount">${creditTotal.toFixed(2)}</span></div></div>
						</div>
					</div>
					<div className="payment-buttons-row">
						<button className="payment-btn" onClick={startCheckout} disabled={isPaymentLoading}>
							<span className="payment-btn-content">
								{isPaymentLoading ? (<><Spinner animation="border" size="sm" className="me-2" /><span>Processing...</span></>) : (<span>Pay Now</span>)}
							</span>
						</button>
					</div>
				</Modal.Body>
			</Modal>
		</div>
	);
};

export default WaveAssistCreditsComponent;
