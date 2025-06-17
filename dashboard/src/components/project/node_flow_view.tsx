// src/components/node_flow_view.tsx
import ReactFlow, { Background, Controls, Node, Edge, NodeChange } from "reactflow";

import "reactflow/dist/style.css";
import "./project_components.css";
import NodeCard from "./node_card";
type Props = {
	nodes: Node[];
	edges: Edge[];
	onNodesChange?: (changes: NodeChange[]) => void;
};
const nodeTypes = { card: NodeCard };

export default function NodeFlowView({ nodes, edges, onNodesChange }: Props) {
	return (
		<div style={{ flex: 1, height: "70vh" }}>
			<ReactFlow
				nodeTypes={nodeTypes}
				proOptions={{ hideAttribution: true }} // 👈 Add this
				nodes={nodes}
				edges={edges}
				nodesDraggable={true}
				onNodesChange={onNodesChange}
				fitView
				fitViewOptions={{ padding: 0.4 }} // 👈 zooms out a bit
			>
				<Background gap={16} color="#2B3548" />

				<Controls />
			</ReactFlow>
		</div>
	);
}
