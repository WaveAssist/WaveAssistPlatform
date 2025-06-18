import ReactFlow, { Background, Controls, Node, Edge } from "reactflow";
import NodeRunCard from "./node_run_card";
import "reactflow/dist/style.css";
import "./project_components.css";

type Props = {
    nodes: Node[];
    edges: Edge[];
};

const nodeTypes = { runCard: NodeRunCard };

export default function NodeRunFlowView({ nodes, edges }: Props) {
    return (
        <div style={{ flex: 1, height: "100%" }}>
            <ReactFlow
                nodeTypes={nodeTypes}
                proOptions={{ hideAttribution: true }}
                nodes={nodes}
                edges={edges}
                nodesDraggable={false}
                fitView
                fitViewOptions={{ padding: 0.4 }}
            >
                <Background gap={16} color="#2B3548" />
                <Controls />
            </ReactFlow>
        </div>
    );
}
