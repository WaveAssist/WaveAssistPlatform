import React from "react";
import { Button } from "react-bootstrap";
import "./PaywallBlock.css";

interface PaywallBlockProps {
	show: boolean;
	message?: string;
	onUpgrade?: () => void;
}

const PaywallBlock: React.FC<PaywallBlockProps> = ({
	show,
	message = "This feature is only available on Builder and Editor plans. Upgrade to unlock!",
	onUpgrade,
}) => {
	if (!show) return null;

	const handleUpgrade = () => {
		if (onUpgrade) {
			onUpgrade();
		} else {
			// Default behavior - open pricing page
			window.open("https://waveassist.io/pricing", "_blank");
		}
	};

	return (
		<div className="paywall-overlay">
			<div className="paywall-modal">
				<div className="paywall-content">
					<h4 className="paywall-title">Want to customize your assistant?</h4>
					<p className="paywall-message">{message}</p>
					<Button variant="warning" onClick={handleUpgrade}>
						<i className="bi bi-arrow-up-circle me-2"></i>
						Upgrade Now
					</Button>
				</div>
			</div>
		</div>
	);
};

export default PaywallBlock;
