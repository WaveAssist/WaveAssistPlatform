// src/components/NodeCard.tsx
import { Handle, Position, NodeProps } from "reactflow";
import "./node_card.css";

export default function NodeCard({ data }: NodeProps) {
	const { name, is_enabled, onEdit, onView, onRun, canRun } = data;

	return (
		<div className={`simple-node ${is_enabled ? "enabled" : "disabled"}`}>
			<Handle type="target" position={Position.Top} />
			<div className="node-content">
				<div className="node-name">{name}</div>
				<div className="node-actions">
					<i className="bi bi-gear-fill" onClick={onEdit} />
					<i className="bi bi-code-slash" onClick={onView} />
					{canRun && <i className="bi bi-play-fill play-button-step" onClick={onRun} />}
				</div>
			</div>
			<Handle type="source" position={Position.Bottom} />
		</div>
	);
}
