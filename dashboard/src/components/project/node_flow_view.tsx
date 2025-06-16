// src/components/node_flow_view.tsx
import ReactFlow, { Background, Controls, Node, Edge } from "reactflow";
import "reactflow/dist/style.css";
import "./project_components.css";
// import NodeCard from "./node_card";
type Props = {
	nodes: Node[];
	edges: Edge[];
	onNodeClick?: (nodeId: string) => void;
};
// const nodeTypes = { card: NodeCard };

export default function NodeFlowView({ nodes, edges, onNodeClick }: Props) {
	return (
		<div style={{ flex: 1, height: "70vh" }}>
			<ReactFlow
				// nodeTypes={nodeTypes}
				proOptions={{ hideAttribution: true }} // 👈 Add this
				nodes={nodes}
				edges={edges}
				onNodeClick={(_, n) => onNodeClick!(n.id)}
				fitView
				fitViewOptions={{ padding: 0.4 }} // 👈 zooms out a bit
			>
				<Background gap={16} color="#2B3548" />

				<Controls />
			</ReactFlow>
		</div>
	);
}
