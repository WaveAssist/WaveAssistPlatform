import React from "react";
import { Button } from "react-bootstrap";
import { useNavigate } from "react-router-dom";
import "./PaywallBlock.css";

interface PaywallBlockProps {
	show: boolean;
	message?: string;
	onUpgrade?: () => void;
	/** When false, no Upgrade button is shown (e.g. for editor plan) */
	showUpgradeButton?: boolean;
}

const PaywallBlock: React.FC<PaywallBlockProps> = ({
	show,
	message = "This feature is only available on specific plans. Upgrade to unlock!",
	onUpgrade,
	showUpgradeButton = true,
}) => {
	const navigate = useNavigate();

	if (!show) return null;

	const handleUpgrade = () => {
		if (onUpgrade) {
			onUpgrade();
		} else {
			navigate("/manage/credits?upgrade=true");
		}
	};

	return (
		<div className="paywall-overlay">
			<div className="paywall-modal">
				<div className="paywall-content">
					<h4 className="paywall-title">Want to customize your assistant?</h4>
					<p className="paywall-message">{message}</p>
					{showUpgradeButton && (
						<Button variant="warning" onClick={handleUpgrade}>
							<i className="bi bi-arrow-up-circle me-2"></i>
							Upgrade Now
						</Button>
					)}
				</div>
			</div>
		</div>
	);
};

export default PaywallBlock;
