import { Handle, Position, NodeProps } from "reactflow";
import "./node_run_card.css";

export default function NodeRunCard({ data }: NodeProps) {
    const { name, duration } = data;
    return (
        <div className="run-node">
            <Handle type="target" position={Position.Top} />
            <div className="run-node-content">
                <div className="run-node-name">{name}{duration ? ` (${duration})` : ""}</div>
            </div>
            <Handle type="source" position={Position.Bottom} />
        </div>
    );
}
