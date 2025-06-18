import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Node as RFNode, Edge as RFEdge, Position } from "reactflow";
import dagre from "dagre";
import NodeFlowView from "./node_flow_view";
import LogsComponent from "./logs_component";
import NodeRunsComponent from "./node_runs_component";
import { fetchNodesApi } from "../../services/project_services";
import { useToast } from "../../utils/toast_context";
import "./project_components.css";

const NODE_WIDTH = 250;
const NODE_HEIGHT = 50;

const RunDetailsComponent: React.FC = () => {
    const { runId } = useParams();
    const { showToast } = useToast();
    const [rfNodes, setRfNodes] = useState<RFNode[]>([]);
    const [rfEdges, setRfEdges] = useState<RFEdge[]>([]);

    const getScheduleLabel = (n: any) => {
        if (n.is_starting_node) {
            if (n.schedule_type === "crontab") return n.crontab_schedule.replace(/\(.*?\)/g, "");
            if (n.schedule_type === "interval") return n.interval_schedule;
            return "Manual / Webhook";
        }
        return `After: ${n.run_after_nodes_array.map((p: any) => p.name).join(", ")}`;
    };

    const buildFlow = (nodesArr: any[]): { rfNodes: RFNode[]; rfEdges: RFEdge[] } => {
        const rfNodes: RFNode[] = nodesArr.map((n: any) => ({
            id: n.node_key,
            type: "card",
            draggable: false,
            data: {
                name: n.name,
                node_key: n.node_key,
                is_enabled: n.is_enabled,
                scheduleLabel: getScheduleLabel(n),
                onView: () => {},
                onEdit: () => {},
                onDelete: () => {},
                onRun: () => {},
                canRun: false,
                label: n.name,
            },
            position: { x: 0, y: 0 },
            style: {
                background: "#232F42",
                border: `2px solid ${n.is_enabled ? "#428d4f" : "#d9534f"}`,
                color: "#fff",
                borderRadius: 8,
                fontSize: 13,
            },
        }));

        const rfEdges: RFEdge[] = nodesArr.flatMap((n: any) =>
            n.run_after_nodes_array.map((parent: any) => ({
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
            const nodesArr = data.node_array || [];
            const { rfNodes, rfEdges } = buildFlow(nodesArr);
            setRfNodes(rfNodes);
            setRfEdges(rfEdges);
        } catch (error) {
            console.error("FetchNodesApi failed:", error);
            showToast("Something went wrong with loading nodes, please try again.", "danger");
        }
    };

    useEffect(() => {
        fetchNodes();
    }, []);

    if (!runId) return null;

    return (
        <div className="main-container" style={{ height: "100%" }}>
            <div style={{ display: "flex", height: "60%" }}>
                <div style={{ width: "50%" }}>
                    <NodeFlowView nodes={rfNodes} edges={rfEdges} />
                </div>
                <div style={{ width: "50%" }}>
                    <NodeRunsComponent dagRunId={runId} />
                </div>
            </div>
            <div style={{ height: "40%" }}>
                <LogsComponent />
            </div>
        </div>
    );
};

export default RunDetailsComponent;
