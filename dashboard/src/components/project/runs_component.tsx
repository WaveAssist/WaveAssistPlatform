import React, { useEffect, useState } from "react";
import { Button } from "react-bootstrap";
import { AgGridReact } from "ag-grid-react";
import { fetchDagRunsApi } from "../../services/runs_services";
import { useToast } from "../../utils/toast_context";
import { useRefresh } from "../../utils/RefreshContext";
import "./project_components.css";
import "../../utils/ag-theme-project.css";

const RunsComponent: React.FC = () => {
    const [runsArray, setRunsArray] = useState<any[]>([]);
    const { showToast } = useToast();
    const { shouldRefresh } = useRefresh();

    const fetchRuns = async () => {
        try {
            const data = await fetchDagRunsApi();
            setRunsArray(data.dag_run_array || []);
        } catch (error) {
            console.error("fetchDagRunsApi failed:", error);
            showToast("Something went wrong with loading runs, please try again.", "danger");
        }
    };

    useEffect(() => {
        fetchRuns();
    }, [shouldRefresh]);

    const handleViewDetails = (run: any) => {
        console.log("View Details for run", run);
    };

    const gridOptions = {
        suppressCellFocus: true,
    };

    const defaultColDef = {
        autoHeight: true,
        wrapText: true,
        enableCellChangeFlash: true,
        editable: false,
        cellClass: "ag-cell",
    };

    const columnDefs = [
        {
            headerName: "Run ID",
            field: "run_id",
            flex: 3,
            cellStyle: { display: "flex", alignItems: "center" },
        },
        {
            headerName: "Started At",
            field: "started_at",
            flex: 3,
            cellStyle: { display: "flex", alignItems: "center" },
        },
        {
            headerName: "Finished At",
            field: "finished_at",
            flex: 3,
            cellStyle: { display: "flex", alignItems: "center" },
        },
        {
            headerName: "Status",
            field: "status",
            flex: 2,
            cellRenderer: (params: any) => (
                <span className={
                    `badge ${params.value === "SUCCESS" ? "badge-primary" : params.value === "FAILED" ? "badge-danger" : "badge-secondary"}`
                }>
                    {params.value}
                </span>
            ),
            cellStyle: { display: "flex", alignItems: "center" },
        },
        {
            headerName: "Actions",
            flex: 2,
            cellRenderer: (params: any) => (
                <Button variant="outline-primary" size="sm" onClick={() => handleViewDetails(params.data)}>
                    View Details
                </Button>
            ),
            cellStyle: { display: "flex", alignItems: "center" },
        },
    ];

    return (
        <div className="main-container">
            <div className="mt-3">
                <div className="d-flex justify-content-between align-items-center mb-3">
                    <h3 className="translucent_white">Runs</h3>
                </div>
                <div className="ag-theme-custom grid-container">
                    <AgGridReact
                        rowData={runsArray}
                        columnDefs={columnDefs}
                        pagination={true}
                        paginationPageSize={10}
                        gridOptions={gridOptions}
                        defaultColDef={defaultColDef}
                    />
                </div>
            </div>
        </div>
    );
};

export default RunsComponent;
