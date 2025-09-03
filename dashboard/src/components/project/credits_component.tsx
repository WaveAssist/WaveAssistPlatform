import React, { useEffect, useState } from "react";
import { usePostHog } from "posthog-js/react";
import { fetchCreditsApi } from "../../services/credits_services";
import { createPaymentOrder, verifyPayment } from "../../services/all_projects_services";
import { useToast } from "../../utils/toast_context";
import { useRefresh } from "../../utils/RefreshContext";
import { Button, Modal } from "react-bootstrap";
import { Spinner } from "react-bootstrap";
import { useRazorpay } from "react-razorpay";
import "./project_components.css";
import "./credits_component.css";
import paypalLogo from "../../assets/uploads/paypal.png";
import razorpayLogo from "../../assets/uploads/razorpay.png";

interface CreditsData {
	limit: number;
	usage: number;
	limit_remaining: number;
}

const CreditsComponent: React.FC = () => {
	// INR conversion rate (USD * 88)
	const INR_CONVERSION_RATE = 88;

	// RazorPay configuration
	const KEY_ID = "rzp_live_RBBftuzZGRsYIz";

	const [creditsData, setCreditsData] = useState<CreditsData | null>(null);
	const [loading, setLoading] = useState(true);
	const [showPurchaseModal, setShowPurchaseModal] = useState(false);
	const [purchaseAmount, setPurchaseAmount] = useState(10);
	const [isCustomSelected, setIsCustomSelected] = useState(false);
	const [isIndia, setIsIndia] = useState<boolean | null>(null);
	const [isPaymentLoading, setIsPaymentLoading] = useState(false);

	const { showToast } = useToast();
	const { shouldRefresh } = useRefresh();
	const posthog = usePostHog();
	const { Razorpay } = useRazorpay();

	const fetchCredits = async () => {
		try {
			setLoading(true);
			const data = await fetchCreditsApi();
			setCreditsData(data);
		} catch (error) {
			console.error("fetchCreditsApi failed:", error);
			showToast("Something went wrong with loading credits, please try again.", "danger");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		fetchCredits();
	}, [shouldRefresh]);

	useEffect(() => {
		// Pageview context for credits page
		try {
			posthog?.capture("$pageview", {
				page_category: "credits",
				project_id: localStorage.getItem("selected_project_key") || undefined,
				environment: localStorage.getItem("selected_env_key") || undefined,
			});
		} catch (_err) {}
	}, []);

	useEffect(() => {
		// Detect user's country from IP
		const fetchCountry = async () => {
			try {
				const response = await fetch("https://ipapi.co/json/");
				if (!response.ok) throw new Error("geo lookup failed");
				const data = await response.json();
				const countryCode = String(data?.country_code || "").toUpperCase();
				setIsIndia(countryCode === "IN");
			} catch (_err) {
				// Default to non-India on failure
				setIsIndia(false);
			}
		};
		fetchCountry();
	}, []);

	const handleAddCredits = () => {
		try {
			posthog?.capture("add_credits_clicked", {
				project_id: localStorage.getItem("selected_project_key") || undefined,
				environment: localStorage.getItem("selected_env_key") || undefined,
			});
		} catch (_err) {}
		setShowPurchaseModal(true);
	};

	const handleRazorPayPayment = async () => {
		try {
			setIsPaymentLoading(true);

			// Get user ID from localStorage
			const uid = localStorage.getItem("uid");
			if (!uid) {
				showToast("User not authenticated. Please login again.", "danger");
				return;
			}

			// Create payment order via API
			const orderData = await createPaymentOrder("razorpay", calculateTotalInINR().toString(), "INR", uid, purchaseAmount.toString());

			if (orderData.success !== "1") {
				throw new Error(orderData.message || "Failed to create payment order");
			}

			const { order_id, amount } = orderData.data;

			const options = {
				key: KEY_ID,
				amount: amount, // Use amount from API response (already in paise)
				currency: "INR" as const,
				name: "WaveAssist",
				description: `${purchaseAmount} Credits Purchase`,
				order_id: order_id,
				handler: async function (response: any) {
					try {
						console.log("response", response);
						const verificationData = await verifyPayment(
							"razorpay",
							calculateTotalInINR().toString(),
							"INR",
							uid,
							order_id, // provider_payment_id (RazorPay payment ID)
							response.razorpay_signature || "", // signature
							response.razorpay_payment_id, // razorpay_payment_id (RazorPay payment ID)
							"" // paypal_payer_id (empty for RazorPay)
						);
						console.log("verificationData", verificationData);
						if (verificationData.success === "1") {
							showToast("Payment verified successfully! Credits will be added shortly.", "success");
							// Refresh credits data
							await fetchCredits();
						} else {
							showToast("Payment verification failed. Please contact support.", "danger");
						}
					} catch (error) {
						console.error("Payment verification failed:", error);
						showToast("Payment verification failed. Please contact support.", "danger");
					}

					setShowPurchaseModal(false);

					// Track successful payment
					try {
						posthog?.capture("razorpay_payment_success", {
							project_id: localStorage.getItem("selected_project_key") || undefined,
							environment: localStorage.getItem("selected_env_key") || undefined,
							amount: purchaseAmount,
							total_amount: calculateTotal(),
							payment_id: response.razorpay_payment_id,
						});
					} catch (_err) {}
				},
				prefill: (() => {
					const userData = JSON.parse(localStorage.getItem("user_data") || "{}");
					return {
						name: userData.name || "User",
						email: userData.username || "user@example.com",
					};
				})(),
				theme: {
					color: "#0a2540", // Bootstrap success color
				},

				modal: {
					ondismiss: function () {
						showToast("Payment cancelled", "warning");
					},
				},
			};

			const rzp = new Razorpay(options);
			rzp.open();

			// Track payment initiation
			try {
				posthog?.capture("razorpay_payment_initiated", {
					project_id: localStorage.getItem("selected_project_key") || undefined,
					environment: localStorage.getItem("selected_env_key") || undefined,
					amount: purchaseAmount,
					total_amount: calculateTotal(),
				});
			} catch (_err) {}
		} catch (error) {
			console.error("RazorPay payment failed:", error);
			showToast("Payment failed. Please try again.", "danger");
		} finally {
			setIsPaymentLoading(false);
		}
	};

	const handlePayPalPayment = async () => {
		try {
			setIsPaymentLoading(true);

			const uid = localStorage.getItem("uid");
			if (!uid) {
				showToast("User not authenticated. Please login again.", "danger");
				return;
			}

			const orderData = await createPaymentOrder("paypal", Number(calculateTotal()).toFixed(2).toString(), "USD", uid, purchaseAmount.toString());

			if (orderData.success !== "1") {
				throw new Error(orderData.message || "Failed to create PayPal order");
			}

			const approvalUrl = orderData?.data?.approval_url || orderData?.approval_url;
			if (!approvalUrl) {
				throw new Error("Approval URL not found in PayPal response");
			}

			try {
				posthog?.capture("paypal_payment_initiated", {
					project_id: localStorage.getItem("selected_project_key") || undefined,
					environment: localStorage.getItem("selected_env_key") || undefined,
					amount: purchaseAmount,
					total_amount: calculateTotal(),
				});
			} catch (_err) {}

			setShowPurchaseModal(false);
			window.location.assign(approvalUrl);
		} catch (error) {
			console.error("PayPal payment failed:", error);
			showToast("Payment failed. Please try again.", "danger");
		} finally {
			setIsPaymentLoading(false);
		}
	};

	const handleCloseModal = () => {
		setShowPurchaseModal(false);
		setPurchaseAmount(10); // Reset to default
	};

	const calculateServiceFees = () => {
		return purchaseAmount * 0.18; // 18% service fee
	};

	const calculateTotal = () => {
		return purchaseAmount + calculateServiceFees();
	};

	const calculateTotalInINR = () => {
		return Math.round(calculateTotal() * INR_CONVERSION_RATE);
	};

	if (loading) {
		return (
			<div className="main-container">
				<div className="mt-3 d-flex flex-column" style={{ height: "100%" }}>
					<div className="d-flex justify-content-center align-items-center" style={{ height: "200px" }}>
						<Spinner animation="border" role="status" variant="success">
							<span className="visually-hidden">Loading...</span>
						</Spinner>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="main-container credits-container">
			<div className="mt-3 d-flex flex-column" style={{ height: "100%" }}>
				{/* Header */}
				<div className="credits-header">
					<h3 className="credits-title">Credits</h3>
					<Button variant="dark" onClick={fetchCredits}>
						<span className="bi bi-arrow-clockwise"></span>
					</Button>
				</div>

				{/* Two Cards Layout */}
				<div className="row">
					{/* Available Credits Card */}
					<div className="col-md-6">
						<div className="available-credits-card">
							<div className="text-center mb-4">
								<h1 className="credit-balance-amount">$ {creditsData?.limit_remaining?.toFixed(2) || "0.00"}</h1>
								<p className="credit-balance-label">Available Credits</p>
							</div>

							{/* Credit Details */}
							{creditsData && (
								<div className="credit-details">
									<div className="credit-detail-row">
										<span className="credit-detail-label">Total Limit:</span>
										<span className="credit-detail-value total">$ {creditsData.limit}</span>
									</div>
									<div className="credit-detail-row">
										<span className="credit-detail-label">Used:</span>
										<span className="credit-detail-value used">$ {creditsData.usage.toFixed(2)}</span>
									</div>
								</div>
							)}
						</div>
					</div>

					{/* Buy Credits Card */}
					<div className="col-md-6">
						<div className="buy-credits-card">
							<div className="buy-credits-header">
								<h5 className="buy-credits-title">Buy Credits</h5>
							</div>

							<div className="buy-credits-content">
								<div className="credit-amount-section">
									<label className="form-label">Select Credit Amount</label>
									<div className="credit-amount-buttons">
										<button
											className={`credit-amount-btn ${!isCustomSelected && purchaseAmount === 5 ? "active" : ""}`}
											onClick={() => {
												setPurchaseAmount(5);
												setIsCustomSelected(false);
											}}>
											$5
										</button>
										<button
											className={`credit-amount-btn ${!isCustomSelected && purchaseAmount === 10 ? "active" : ""}`}
											onClick={() => {
												setPurchaseAmount(10);
												setIsCustomSelected(false);
											}}>
											$10
										</button>
										<button
											className={`credit-amount-btn ${!isCustomSelected && purchaseAmount === 20 ? "active" : ""}`}
											onClick={() => {
												setPurchaseAmount(20);
												setIsCustomSelected(false);
											}}>
											$20
										</button>
										<div className={`custom-amount-input ${isCustomSelected ? "active" : ""}`} onClick={() => setIsCustomSelected(true)}>
											{(isCustomSelected || (purchaseAmount !== 5 && purchaseAmount !== 10 && purchaseAmount !== 20)) && (
												<span className="dollar-sign">$</span>
											)}
											<input
												type="text"
												placeholder="Custom"
												value={purchaseAmount !== 5 && purchaseAmount !== 10 && purchaseAmount !== 20 ? String(purchaseAmount) : ""}
												onChange={(e) => {
													const raw = e.target.value.trim();
													if (raw === "") return;
													const parsed = Number(raw.replace(/[^0-9.]/g, ""));
													if (!isNaN(parsed) && parsed > 0) setPurchaseAmount(parsed);
												}}
												onFocus={() => setIsCustomSelected(true)}
												onBlur={() => setIsCustomSelected(false)}
												autoFocus={isCustomSelected}
											/>
										</div>
									</div>
								</div>

								<div className="add-credits-section">
									<button className="add-credits-button" onClick={handleAddCredits}>
										Add Credits
									</button>
								</div>

								{/* View Usage removed */}
							</div>
						</div>
					</div>
				</div>
			</div>

			{/* Purchase Credits Modal */}
			<Modal show={showPurchaseModal} onHide={handleCloseModal} size="lg" centered>
				<Modal.Header closeButton>
					<Modal.Title>Purchase Credits</Modal.Title>
				</Modal.Header>
				<Modal.Body>
					<div className="purchase-modal-content">
						{/* Purchase Summary */}
						<div className="purchase-summary">
							<div className="summary-row">
								<span>Amount</span>
								<span>${purchaseAmount}</span>
							</div>
							<div className="summary-row">
								<span>Platform, Gateway & Taxes</span>
								<span>${calculateServiceFees().toFixed(2)}</span>
							</div>

							<div className="summary-row total-row">
								<span>Total due</span>
								<div className="total-amount-container">
									<span className="total-amount">${calculateTotal().toFixed(2)}</span>
									{(isIndia ?? false) && <span className="indian-currency-amount">₹{calculateTotalInINR().toFixed(2)}</span>}
								</div>
							</div>
						</div>
					</div>
					{isIndia ?? false ? (
						<>
							<div className="payment-buttons-row">
								<Button onClick={handleRazorPayPayment} className="payment-btn razorpay-btn" disabled={isPaymentLoading}>
									<span className="payment-btn-content">
										{isPaymentLoading ? (
											<>
												<Spinner animation="border" size="sm" className="me-2" />
												<span>Creating Order...</span>
											</>
										) : (
											<>
												<span>Pay with</span>
												<img src={razorpayLogo} alt="Razorpay" className="payment-logo" />
											</>
										)}
									</span>
								</Button>
							</div>
							<br />
							<div className="secondary-option payment-buttons-row">
								<p className="secondary-note">
									Alternatively,{" "}
									<a
										href="#"
										className={`payment-link ${isPaymentLoading ? "disabled" : ""}`}
										onClick={(e) => {
											e.preventDefault();
											if (!isPaymentLoading) {
												handlePayPalPayment();
											}
										}}>
										{isPaymentLoading ? "Creating Order..." : "Pay with PayPal"}
									</a>
									<br />
									PayPal does not accept Indian cards.
								</p>
							</div>
						</>
					) : (
						<>
							<div className="payment-buttons-row">
								<Button onClick={handlePayPalPayment} disabled={isPaymentLoading} className="payment-btn paypal-btn">
									<span className="payment-btn-content">
										{isPaymentLoading ? (
											<>
												<Spinner animation="border" size="sm" className="me-2" />
												<span>Creating Order...</span>
											</>
										) : (
											<>
												<span>Pay with</span>
												<img src={paypalLogo} alt="PayPal" className="payment-logo" />
											</>
										)}
									</span>
								</Button>
							</div>
							<br />
							<div className="secondary-option payment-buttons-row">
								<p className="secondary-note">
									Alternatively,{" "}
									<a
										href="#"
										className={`payment-link ${isPaymentLoading ? "disabled" : ""}`}
										onClick={(e) => {
											e.preventDefault();
											if (!isPaymentLoading) {
												handleRazorPayPayment();
											}
										}}>
										{isPaymentLoading ? "Creating Order..." : "Pay with Razorpay"}
									</a>
									<br />
									Razorpay only works with Indian cards.
								</p>
							</div>
						</>
					)}
				</Modal.Body>
			</Modal>
		</div>
	);
};

export default CreditsComponent;
