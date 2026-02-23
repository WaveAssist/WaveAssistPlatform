// src/components/NodeCard.tsx
import { Handle, Position, NodeProps } from "reactflow";
import "./node_card.css";
import React, { useState } from "react";
import Modal from "react-bootstrap/Modal";
import Button from "react-bootstrap/Button";

function PaywallModal({ show, onHide, onPay }: { show: boolean; onHide: () => void; onPay?: () => void }) {
  return (
    <Modal show={show} onHide={onHide} centered>
      <Modal.Header closeButton className="bg-dark text-white">
      <Modal.Title>Premium Access Required</Modal.Title>
      </Modal.Header>
      <Modal.Body className="bg-dark text-white text-center">
      <div style={{ fontSize: "1.0rem", marginBottom: 20 }}>
	  Hey, to edit this premium template, you need a Growth or Pro plan for full Python tweaks and scalable agents.

</div>
        <Button
          variant="warning"
          style={{ fontWeight: 600, fontSize: "1.1rem", minWidth: 120 }}
          onClick={onPay}
        >
          Upgrade Now
        </Button>
      </Modal.Body>
    </Modal>
  );
}

export default function NodeCard({ data }: NodeProps) {
        const { name, is_enabled, onEdit, onView, onRun, canRun, canEdit } = data as any;

        const isProjectPremium = localStorage.getItem("is_project_premium") === "true";
        const userData = JSON.parse(localStorage.getItem("user_data") || "{}");
        const isUserPremium =
                localStorage.getItem("is_premium") === "true" || Boolean(userData.is_premium);
        // Editor (canEdit false) can always view code; no upgrade CTA for editor
        const isDisabled = canEdit === false ? false : isProjectPremium && !isUserPremium;

        const [showPaywall, setShowPaywall] = useState(false);

        const disabledStyle = isDisabled ? { opacity: 0.5, cursor: "not-allowed" } : {};

        const handlePremiumBlocked = (e: React.MouseEvent) => {
                e.stopPropagation();
                setShowPaywall(true);
        };

        return (
                <div className={`simple-node ${is_enabled ? "enabled" : "disabled"}`}>
                        <Handle type="target" position={Position.Top} />
                        <div className="node-content">
                                <div className="node-name">{name}</div>
                                <div className={`node-actions ${canEdit === false ? "node-actions-view-only" : ""}`}>
                                        {canEdit && (
                                                <i
                                                        className="bi bi-gear-fill"
                                                        onClick={isDisabled ? handlePremiumBlocked : onEdit}
                                                        title={isDisabled ? "Premium feature - upgrade to access" : "Edit node"}
                                                        style={disabledStyle}
                                                />
                                        )}
                                        <i
                                                className="bi bi-code-slash"
                                                onClick={isDisabled ? handlePremiumBlocked : onView}
                                                title={isDisabled ? "Premium feature - upgrade to access" : "View node code"}
                                                style={disabledStyle}
                                        />
                                        {canEdit && canRun && (
                                                <i
                                                        className="bi bi-play-fill play-button-step"
                                                        onClick={!isDisabled ? onRun : undefined}
                                                        title={isDisabled ? "Premium feature - upgrade to access" : "Run node"}
                                                        style={disabledStyle}
                                                />
                                        )}
                                </div>
                        </div>
                        <Handle type="source" position={Position.Bottom} />
                        <PaywallModal
                                show={showPaywall}
                                onHide={() => setShowPaywall(false)}
                                onPay={() => {
                                        window.open('https://waveassist.io/pricing', '_blank');
                                        setShowPaywall(false);
                                }}
                        />
                </div>
        );
}
