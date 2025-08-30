import React, { useEffect } from "react";

declare global {
	interface Window {
		Razorpay: any;
	}
}

const TestComponent: React.FC = () => {
	const orderId = "order_RBCIwgt9UMKvpT";

	useEffect(() => {
		// Load Razorpay script
		const script = document.createElement("script");
		script.src = "https://checkout.razorpay.com/v1/checkout.js";
		script.async = true;
		document.body.appendChild(script);

		return () => {
			document.body.removeChild(script);
		};
	}, []);

	const openRazorpayModal = () => {
		if (window.Razorpay) {
			const options = {
				key: "rzp_live_RBBftuzZGRsYIz", // Replace with your actual Razorpay test key
				amount: 500, // Amount in paise (500 INR)
				currency: "INR",
				name: "WaveAssist",
				description: "Test Payment",
				order_id: orderId,
				handler: function (response: any) {
					console.log("Payment successful:", response);
					alert("Payment successful! Payment ID: " + response.razorpay_payment_id);
				},
				prefill: {
					name: "Test User",
					email: "test@example.com",
					contact: "9999999999",
				},
				theme: {
					color: "#3399cc",
				},
			};

			const rzp = new window.Razorpay(options);
			rzp.open();
		} else {
			alert("Razorpay script not loaded");
		}
	};

	return (
		<div style={{ padding: "20px", textAlign: "center" }}>
			<h2 style={{ color: "white", marginBottom: "20px" }}>Razorpay Payment Test</h2>
			<p style={{ color: "white", marginBottom: "20px" }}>
				Order ID: <strong>{orderId}</strong>
			</p>
			<button
				onClick={openRazorpayModal}
				style={{
					padding: "12px 24px",
					fontSize: "16px",
					backgroundColor: "#3399cc",
					color: "white",
					border: "none",
					borderRadius: "5px",
					cursor: "pointer",
				}}>
				Open Razorpay Modal
			</button>
		</div>
	);
};

export default TestComponent;
