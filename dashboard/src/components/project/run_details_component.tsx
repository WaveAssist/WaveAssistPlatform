import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Node as RFNode, Edge as RFEdge, Position } from "reactflow";
import dagre from "dagre";
import NodeRunFlowView from "./node_run_flow_view";
import LogsComponent from "./logs_component";
import { fetchNodesApi } from "../../services/project_services";
import { fetchNodeRunsApi } from "../../services/runs_services";
import { useToast } from "../../utils/toast_context";
import "./project_components.css";

const NODE_WIDTH = 250;
const NODE_HEIGHT = 50;

const RunDetailsComponent: React.FC = () => {
    const { runId } = useParams();
    const { showToast } = useToast();
    const [rfNodes, setRfNodes] = useState<RFNode[]>([]);
    const [rfEdges, setRfEdges] = useState<RFEdge[]>([]);
    const [nodeRuns, setNodeRuns] = useState<any[]>([]);
    const [nodesData, setNodesData] = useState<any[]>([]);

    const buildFlow = (nodesArr: any[], runMap: Map<string, any>): { rfNodes: RFNode[]; rfEdges: RFEdge[] } => {
        const filtered = nodesArr.filter((n: any) => runMap.has(n.node_key));

        const rfNodes: RFNode[] = filtered.map((n: any) => {
            const run = runMap.get(n.node_key);
            const started = run?.started_at;
            const finished = run?.finished_at;
            let duration = "NA";
            if (started && finished) {
                const diffMs = new Date(finished).getTime() - new Date(started).getTime();
                duration = diffMs >= 1000 ? `${(diffMs / 1000).toFixed(2)} s` : `${diffMs} ms`;
            }
            const color = run?.status === "SUCCESS" ? "#428d4f" : run?.status === "FAILED" ? "#d9534f" : "#888";

            return {
                id: n.node_key,
                type: "runCard",
                draggable: false,
                data: {
                    name: n.name,
                    duration,
                },
                position: { x: 0, y: 0 },
                style: {
                    background: "#232F42",
                    border: `2px solid ${color}`,
                    color: "#fff",
                    borderRadius: 8,
                    fontSize: 13,
                },
            } as RFNode;
        });

        const rfEdges: RFEdge[] = filtered.flatMap((n: any) =>
            n.run_after_nodes_array
                .filter((p: any) => runMap.has(p.node_key))
                .map((parent: any) => ({
                    id: `${parent.node_key}->${n.node_key}`,
                    source: parent.node_key,
                    target: n.node_key,
                    animated: true,
                    style: {
                        stroke: "#49d078",
                        strokeWidth: 1.5,
                    },
                    markerEnd: { type: "arrowclosed", color: "#49d078" },
                }))
        );

        const dagreGraph = new dagre.graphlib.Graph();
        dagreGraph.setDefaultEdgeLabel(() => ({}));
        dagreGraph.setGraph({ rankdir: "TB" });

        rfNodes.forEach((node) => {
            dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
        });
        rfEdges.forEach((edge) => {
            dagreGraph.setEdge(edge.source, edge.target);
        });

        dagre.layout(dagreGraph);

        const layoutedNodes = rfNodes.map((node) => {
            const pos = dagreGraph.node(node.id);
            return {
                ...node,
                position: { x: pos.x, y: pos.y },
                sourcePosition: Position.Bottom,
                targetPosition: Position.Top,
            };
        });

        return { rfNodes: layoutedNodes, rfEdges };
    };

    const fetchNodes = async () => {
        try {
            const data = await fetchNodesApi();
            setNodesData(data.node_array || []);
        } catch (error) {
            console.error("FetchNodesApi failed:", error);
            showToast("Something went wrong with loading nodes, please try again.", "danger");
        }
    };

    const fetchNodeRuns = async () => {
        try {
            if (!runId) return;
            const data = await fetchNodeRunsApi(runId);
            setNodeRuns(data.node_runs || []);
        } catch (error) {
            console.error("fetchNodeRunsApi failed:", error);
            showToast("Something went wrong with loading node runs, please try again.", "danger");
        }
    };

    useEffect(() => {
        fetchNodes();
        fetchNodeRuns();
    }, [runId]);

    useEffect(() => {
        if (nodesData.length === 0 || nodeRuns.length === 0) return;
        const runMap = new Map(nodeRuns.map((r: any) => [r.node_key, r]));
        const { rfNodes, rfEdges } = buildFlow(nodesData, runMap);
        setRfNodes(rfNodes);
        setRfEdges(rfEdges);
    }, [nodesData, nodeRuns]);

    if (!runId) return null;

    return (
        <div className="main-container" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
            <div style={{ flex: "0 0 60%" }}>
                <NodeRunFlowView nodes={rfNodes} edges={rfEdges} />
            </div>
            <div style={{ flex: "0 0 40%", overflowY: "auto" }}>
                <LogsComponent />
            </div>
        </div>
    );
};

export default RunDetailsComponent;
