import React, { useEffect, useState } from "react";
import { usePostHog } from "posthog-js/react";
import { fetchCreditsApi } from "../../services/credits_services";
import { useToast } from "../../utils/toast_context";
import { useRefresh } from "../../utils/RefreshContext";
import { Button, Modal, Form } from "react-bootstrap";
import "./project_components.css";
import "./credits_component.css";

interface CreditsData {
    limit: number;
    usage: number;
    limit_remaining: number;
}

const CreditsComponent: React.FC = () => {
    const [creditsData, setCreditsData] = useState<CreditsData | null>(null);
    const [loading, setLoading] = useState(true);
    const [showPurchaseModal, setShowPurchaseModal] = useState(false);
    const [purchaseAmount, setPurchaseAmount] = useState(10);
    const [sendInvoices, setSendInvoices] = useState(false);
    const { showToast } = useToast();
    const { shouldRefresh } = useRefresh();
    const posthog = usePostHog();

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

    const handleAddCredits = () => {
        try {
            posthog?.capture("add_credits_clicked", {
                project_id: localStorage.getItem("selected_project_key") || undefined,
                environment: localStorage.getItem("selected_env_key") || undefined,
            });
        } catch (_err) {}
        setShowPurchaseModal(true);
    };

    const handlePurchase = () => {
        // TODO: Implement actual purchase functionality
        showToast(`Purchase of $${purchaseAmount} credits initiated!`, "success");
        setShowPurchaseModal(false);
        setPurchaseAmount(10); // Reset to default
    };

    const handleCloseModal = () => {
        setShowPurchaseModal(false);
        setPurchaseAmount(10); // Reset to default
    };

    const calculateServiceFees = () => {
        return purchaseAmount * 0.08; // 8% service fee
    };

    const calculateTotal = () => {
        return purchaseAmount + calculateServiceFees();
    };

    const handleViewUsage = () => {
        try {
            posthog?.capture("view_usage_clicked", {
                project_id: localStorage.getItem("selected_project_key") || undefined,
                environment: localStorage.getItem("selected_env_key") || undefined,
            });
        } catch (_err) {}
        // TODO: Implement view usage functionality
        showToast("Usage details coming soon!", "info");
    };

    if (loading) {
        return (
            <div className="main-container">
                <div className="mt-3 d-flex flex-column" style={{ height: "100%" }}>
                    <div className="d-flex justify-content-center align-items-center" style={{ height: "200px" }}>
                        <div className="spinner-border text-light" role="status">
                            <span className="visually-hidden">Loading...</span>
                        </div>
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
                                <h1 className="credit-balance-amount">
                                    $ {creditsData?.limit_remaining?.toFixed(2) || "0.00"}
                                </h1>
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
                                            className={`credit-amount-btn ${purchaseAmount === 5 ? 'active' : ''}`}
                                            onClick={() => setPurchaseAmount(5)}
                                        >
                                            $5
                                        </button>
                                        <button 
                                            className={`credit-amount-btn ${purchaseAmount === 10 ? 'active' : ''}`}
                                            onClick={() => setPurchaseAmount(10)}
                                        >
                                            $10
                                        </button>
                                        <button 
                                            className={`credit-amount-btn ${purchaseAmount === 20 ? 'active' : ''}`}
                                            onClick={() => setPurchaseAmount(20)}
                                        >
                                            $20
                                        </button>
                                        <div className="custom-amount-input">
                                            <input
                                                type="number"
                                                placeholder="Custom"
                                                value={purchaseAmount !== 5 && purchaseAmount !== 10 && purchaseAmount !== 20 ? purchaseAmount : ''}
                                                onChange={(e) => {
                                                    const value = Number(e.target.value);
                                                    if (value > 0) {
                                                        setPurchaseAmount(value);
                                                    }
                                                }}
                                                min="1"
                                                className="form-control"
                                            />
                                        </div>
                                    </div>
                                </div>
                                
                                <div className="add-credits-section">
                                    <button 
                                        className="add-credits-button"
                                        onClick={handleAddCredits}
                                    >
                                        Add Credits
                                    </button>
                                </div>
                                
                                <div className="view-usage-section">
                                    <a 
                                        href="#" 
                                        className="view-usage-link"
                                        onClick={(e) => {
                                            e.preventDefault();
                                            handleViewUsage();
                                        }}
                                    >
                                        View Usage <i className="bi bi-box-arrow-up-right"></i>
                                    </a>
                                </div>
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
                        {/* Credit Package Selection */}
                        <div className="credit-package-card">
                            <div className="package-header">
                                <span className="package-name">LINK</span>
                                <button className="remove-package-btn">
                                    <i className="bi bi-trash"></i>
                                </button>
                            </div>
                            <div className="package-details">
                                <i className="bi bi-check-circle-fill text-success"></i>
                                <span className="package-date">Fri Jun 20 2025</span>
                            </div>
                            <button className="add-package-btn">
                                <i className="bi bi-plus"></i>
                            </button>
                        </div>

                        {/* Amount Input */}
                        <div className="amount-section">
                            <label className="form-label">Amount</label>
                            <Form.Control
                                type="number"
                                value={purchaseAmount}
                                onChange={(e) => setPurchaseAmount(Number(e.target.value))}
                                min="1"
                                className="amount-input"
                            />
                        </div>

                        {/* Billing Options */}
                        <div className="billing-options">
                            <div className="billing-option">
                                <span>Billing address</span>
                                <i className="bi bi-chevron-right"></i>
                            </div>
                            <div className="billing-option">
                                <span>Edit Tax ID</span>
                                <i className="bi bi-chevron-right"></i>
                            </div>
                            <div className="billing-option">
                                <span>Send me invoices</span>
                                <div className="d-flex align-items-center">
                                    <i className="bi bi-info-circle me-2"></i>
                                    <Form.Check
                                        type="switch"
                                        checked={sendInvoices}
                                        onChange={(e) => setSendInvoices(e.target.checked)}
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Purchase Summary */}
                        <div className="purchase-summary">
                            <div className="summary-row">
                                <span>Service fees</span>
                                <span>${calculateServiceFees().toFixed(2)}</span>
                            </div>
                            <div className="summary-row">
                                <span>Sales taxes</span>
                                <span>N/A</span>
                            </div>
                            <div className="summary-row total-row">
                                <span>Total due</span>
                                <span className="total-amount">${calculateTotal().toFixed(2)}</span>
                            </div>
                        </div>
                    </div>
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={handleCloseModal}>
                        Cancel
                    </Button>
                    <Button 
                        variant="primary" 
                        onClick={handlePurchase}
                        className="purchase-btn"
                    >
                        Purchase
                    </Button>
                </Modal.Footer>
            </Modal>
        </div>
    );
};

export default CreditsComponent;
