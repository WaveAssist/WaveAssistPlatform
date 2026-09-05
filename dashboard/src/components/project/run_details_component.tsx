import React from "react";
import { useParams } from "react-router-dom";
import NodeRunsComponent from "./node_runs_component";
import "./project_components.css";

const RunDetailsComponent: React.FC = () => {
    const { runId } = useParams();

    if (!runId) return null;

    return (
        <div className="main-container">
            <NodeRunsComponent dagRunId={runId} />
        </div>
    );
};

export default RunDetailsComponent;
