import React, { useEffect, useState } from "react";

const TestComponent: React.FC = () => {
	const [logs, setLogs] = useState<string>("");

	useEffect(() => {
		const fetchLogs = async () => {
			try {
				const response = await fetch('http://localhost/loki/api/v1/query_range?query={job="all-docker-logs"}&limit=100');
				const data = await response.json();

				// Parse the response from Loki to extract the log lines
				const parsedLogs = data.data.result.map((logEntry: any) => logEntry.values.map((value: any) => value[1]).join("\n")).join("\n");

				setLogs(parsedLogs);
			} catch (error) {
				console.error("Error fetching logs:", error);
			}
		};

		// Fetch logs every 2 seconds
		const intervalId = setInterval(fetchLogs, 2000);

		// Clean up the interval when the component unmounts
		return () => clearInterval(intervalId);
	}, []);

	return (
		<div style={{ height: "600px", border: "1px solid black" }}>
			{/* display all data in table.  */}
			<p className="text-white">{logs}</p>
		</div>
	);
};

export default TestComponent;
