import { Handle, Position, NodeProps } from "reactflow";
import { Button, Badge } from "react-bootstrap";
import "./node_card.css";

export default function NodeCard({ data }: NodeProps) {
	const { name, is_enabled, scheduleLabel, onView, onEdit, onRun, canRun } = data;

	return (
		<div className={`card-root ${is_enabled ? "enabled" : "disabled"}`}>
			<Handle type="target" position={Position.Top} />
			<div className="card-content">
				{/* Section 1: Title */}
				<div className="title-section">
					<span className="title">{name}</span>
				</div>

				{/* Section 2: View & Edit Buttons */}
				<div className="btn-section">
					<Button size="sm" variant="outline-success" onClick={onView}>
						<i className="bi bi-code-slash" /> View Code
					</Button>
					<Button size="sm" variant="outline-success" onClick={onEdit}>
						<i className="bi bi-pencil" /> Edit Node
					</Button>
				</div>

				{/* Section 3: Schedule + Run */}
				{canRun && (
					<div className="run-section">
						<Badge bg="secondary" className="schedule-label">
							{scheduleLabel}
						</Badge>
						<Button size="sm" variant="success" onClick={onRun}>
							<i className="bi bi-play" /> Run
						</Button>
					</div>
				)}
			</div>
			<Handle type="source" position={Position.Bottom} />
		</div>
	);
}
