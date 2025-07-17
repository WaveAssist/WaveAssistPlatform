// src/components/NodeCard.tsx
import { Handle, Position, NodeProps } from "reactflow";
import "./node_card.css";

export default function NodeCard({ data }: NodeProps) {
        const { name, is_enabled, onEdit, onView, onRun, canRun } = data;

        const isProjectPremium = localStorage.getItem("is_project_premium") === "true";
        const userData = JSON.parse(localStorage.getItem("user_data") || "{}");
        const isUserPremium = userData.is_premium === true;
        const isDisabled = isProjectPremium && !isUserPremium;

        const disabledStyle = isDisabled ? { opacity: 0.5, cursor: "not-allowed" } : {};

        return (
                <div className={`simple-node ${is_enabled ? "enabled" : "disabled"}`}>
                        <Handle type="target" position={Position.Top} />
                        <div className="node-content">
                                <div className="node-name">{name}</div>
                                <div className="node-actions">
                                        <i
                                                className="bi bi-gear-fill"
                                                onClick={!isDisabled ? onEdit : undefined}
                                                title={isDisabled ? "Premium feature - upgrade to access" : "Edit node"}
                                                style={disabledStyle}
                                        />
                                        <i
                                                className="bi bi-code-slash"
                                                onClick={!isDisabled ? onView : undefined}
                                                title={isDisabled ? "Premium feature - upgrade to access" : "View node code"}
                                                style={disabledStyle}
                                        />
                                        {canRun && (
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
                </div>
        );
}
