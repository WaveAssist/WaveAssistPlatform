import React, { useEffect, useState } from "react";
import { usePostHog } from "posthog-js/react";
import { fetchCreditsApi } from "../../services/credits_services";
import { createPaymentOrder, verifyPayment } from "../../services/all_projects_services";
import { useToast } from "../../utils/toast_context";
import { useRefresh } from "../../utils/RefreshContext";
import { Button, Modal } from "react-bootstrap";
import { Spinner } from "react-bootstrap";
import { useRazorpay } from "react-razorpay";
import { PayPalScriptProvider, PayPalButtons, usePayPalScriptReducer } from "@paypal/react-paypal-js";
import "./project_components.css";
import "./credits_component.css";
import razorpayLogo from "../../assets/uploads/razorpay.png";

interface CreditsData {
	limit: number;
	usage: number;
	limit_remaining: number;
}

const CreditsComponent: React.FC = () => {
	// TEMPORARY: Disable Add Credits functionality - set to false to re-enable
	const ADD_CREDITS_ENABLED = true;

	// INR conversion rate (USD * 88)
	const INR_CONVERSION_RATE = 88;

	// RazorPay configuration
	const KEY_ID = "rzp_live_RBBftuzZGRsYIz";

	// PayPal configuration
	const PAYPAL_CLIENT_ID = "AQPRi0ROg3TN4djeqcXqBVlu150SiOH1gipJOPf5JDSOoiuCPswPWtL-a7TTdX8fV3buN9NB_lK3A651";

	const [creditsData, setCreditsData] = useState<CreditsData | null>(null);
	const [loading, setLoading] = useState(true);
	const [showPurchaseModal, setShowPurchaseModal] = useState(false);
	const [purchaseAmount, setPurchaseAmount] = useState(10);
	const [isCustomSelected, setIsCustomSelected] = useState(false);
	const [isIndia, setIsIndia] = useState<boolean | null>(null);
	const [isPaymentLoading, setIsPaymentLoading] = useState(false);
	const [loadPayPalSDK, setLoadPayPalSDK] = useState(false);
	const [isRazorPayCreatingOrder, setIsRazorPayCreatingOrder] = useState(false);
	const [isRazorPayVerifying, setIsRazorPayVerifying] = useState(false);

	const { showToast } = useToast();
	const { shouldRefresh } = useRefresh();
	const posthog = usePostHog();
	const { Razorpay } = useRazorpay();

	// PayPal Button Component
	const PayPalButtonComponent: React.FC = () => {
		const [{ isPending }] = usePayPalScriptReducer();
		console.debug("PayPalButtonComponent rendered", { isPending, loadPayPalSDK });

		const createOrder = async () => {
			try {
				console.debug("createOrder called");
				const uid = localStorage.getItem("uid");
				if (!uid) {
					showToast("User not authenticated. Please login again.", "danger");
					throw new Error("User not authenticated");
				}

				console.debug("Creating payment order with:", {
					provider: "paypal",
					amount: Number(calculateTotal()).toFixed(2).toString(),
					currency: "USD",
					uid,
					credits: purchaseAmount.toString(),
				});

				const orderData = await createPaymentOrder("paypal", Number(calculateTotal()).toFixed(2).toString(), "USD", uid, purchaseAmount.toString());

				console.debug("Order data received:", orderData);

				if (orderData.success !== "1") {
					throw new Error(orderData.message || "Failed to create PayPal order");
				}

				// Check if order_id exists in data or at root level
				const orderId = orderData.data?.order_id || orderData.order_id;

				if (!orderId) {
					throw new Error("Order ID not found in PayPal response");
				}

				console.debug("Returning orderId:", orderId);
				return orderId;
			} catch (error) {
				console.error("PayPal order creation failed:", error);
				showToast("Failed to create payment order. Please try again.", "danger");
				throw error;
			}
		};

		const onApprove = async (data: any) => {
			try {
				console.debug("onApprove called with data:", data);
				const uid = localStorage.getItem("uid");
				if (!uid) {
					showToast("User not authenticated. Please login again.", "danger");
					return;
				}

				console.debug("Verifying payment with:", {
					provider: "paypal",
					amount: Number(calculateTotal()).toFixed(2).toString(),
					currency: "USD",
					uid,
					paymentId: data.orderID,
					payerID: data.payerID,
				});

				const verificationData = await verifyPayment(
					"paypal",
					Number(calculateTotal()).toFixed(2).toString(),
					"USD",
					uid,
					data.orderID, // provider_payment_id (PayPal payment ID)
					"", // signature (empty for PayPal)
					"", // razorpay_payment_id (empty for PayPal)
					data.payerID // paypal_payer_id
				);

				console.debug("Verification data received:", verificationData);

				if (verificationData.success === "1") {
					showToast("Payment verified successfully! Credits will be added shortly.", "success");
					await fetchCredits();
					setShowPurchaseModal(false);

					// Track successful payment
					try {
						posthog?.capture("paypal_payment_success", {
							project_id: localStorage.getItem("selected_project_key") || undefined,
							environment: localStorage.getItem("selected_env_key") || undefined,
							amount: purchaseAmount,
							total_amount: calculateTotal(),
							payment_id: data.orderID,
						});
					} catch (_err) {}
				} else {
					showToast("Payment verification failed. Please contact support.", "danger");
				}
			} catch (error) {
				console.error("PayPal payment verification failed:", error);
				showToast("Payment verification failed. Please contact support.", "danger");
			}
		};

		const onError = (err: any) => {
			console.error("PayPal payment error:", err);
			console.error("PayPal error details:", JSON.stringify(err, null, 2));
			showToast(`Payment failed: ${err.message || "Unknown error"}. Please try again.`, "danger");
		};

		const onCancel = () => {
			showToast("Payment cancelled", "warning");
		};

		return (
			<div style={{ position: "relative", backgroundColor: "#ffffff", padding: "10px", borderRadius: "4px" }}>
				<PayPalButtons
					createOrder={createOrder}
					onApprove={onApprove}
					onError={onError}
					onCancel={onCancel}
					style={{
						layout: "vertical",
						color: "gold",
						shape: "rect",
						label: "pay",
						tagline: false,
					}}
					onInit={(data, actions) => {
						console.debug("PayPal buttons initialized:", data, actions);
					}}
				/>
			</div>
		);
	};

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
		// For non-India users, automatically load PayPal SDK when modal opens
		if (isIndia === false) {
			setLoadPayPalSDK(true);
		}
	};

	const handleRazorPayPayment = async () => {
		try {
			setIsPaymentLoading(true);
			setIsRazorPayCreatingOrder(true);

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
						setIsRazorPayVerifying(true);
						console.debug("response", response);
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
						console.debug("verificationData", verificationData);
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
					} finally {
						setIsRazorPayVerifying(false);
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
			setIsRazorPayCreatingOrder(false);
		}
	};

	const handleCloseModal = () => {
		setShowPurchaseModal(false);
		setPurchaseAmount(10); // Reset to default
		setLoadPayPalSDK(false); // Reset PayPal SDK loading

		setIsRazorPayCreatingOrder(false); // Reset RazorPay loading states
		setIsRazorPayVerifying(false);
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
									<button
										className="add-credits-button"
										onClick={ADD_CREDITS_ENABLED ? handleAddCredits : undefined}
										disabled={!ADD_CREDITS_ENABLED}
										style={{
											opacity: ADD_CREDITS_ENABLED ? 1 : 0.6,
											cursor: ADD_CREDITS_ENABLED ? "pointer" : "not-allowed",
										}}>
										{ADD_CREDITS_ENABLED ? "Add Credits" : "Add Credits (Coming Soon)"}
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
								<Button
									onClick={handleRazorPayPayment}
									className="payment-btn razorpay-btn"
									disabled={isPaymentLoading || isRazorPayCreatingOrder || isRazorPayVerifying}>
									<span className="payment-btn-content">
										{isPaymentLoading || isRazorPayCreatingOrder || isRazorPayVerifying ? (
											<>
												<Spinner animation="border" size="sm" className="me-2" />
												<span>
													{isRazorPayCreatingOrder ? "Creating Order..." : isRazorPayVerifying ? "Verifying Payment..." : "Creating Order..."}
												</span>
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
						</>
					) : (
						<>
							<div className="payment-buttons-row">
								{loadPayPalSDK ? (
									<>
										{console.debug("Rendering PayPalScriptProvider for non-India users", { loadPayPalSDK, clientId: PAYPAL_CLIENT_ID })}
										<PayPalScriptProvider
											options={{
												clientId: PAYPAL_CLIENT_ID,
												currency: "USD",
												intent: "capture",
											}}>
											<PayPalButtonComponent />
										</PayPalScriptProvider>
									</>
								) : (
									<>Loading PayPal...</>
								)}
							</div>
							<br />
							<div className="secondary-option payment-buttons-row">
								<p className="secondary-note">
									Alternatively,{" "}
									<a
										href="#"
										className={`payment-link ${isPaymentLoading || isRazorPayCreatingOrder || isRazorPayVerifying ? "disabled" : ""}`}
										onClick={(e) => {
											e.preventDefault();
											if (!isPaymentLoading && !isRazorPayCreatingOrder && !isRazorPayVerifying) {
												handleRazorPayPayment();
											}
										}}>
										{isPaymentLoading || isRazorPayCreatingOrder || isRazorPayVerifying
											? isRazorPayCreatingOrder
												? "Creating Order..."
												: isRazorPayVerifying
												? "Verifying Payment..."
												: "Creating Order..."
											: "Pay with Razorpay"}
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
