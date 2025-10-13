import React, { useState, useEffect } from "react";
import { Form, DropdownButton, Dropdown, Button, Modal } from "react-bootstrap";
import timezones from "../../utils/timezones.json";

interface ScheduleInputProps {
	value: string;
	onChange: (value: string) => void;
}

const ScheduleInput: React.FC<ScheduleInputProps> = ({ value, onChange }) => {
	const [showModal, setShowModal] = useState(false);
	const [scheduleType, setScheduleType] = useState<"interval" | "crontab" | "none">("interval");
	const [intervalEvery, setIntervalEvery] = useState<string>("30");
	const [intervalType, setIntervalType] = useState<string>("minutes");
	const [crontabMinutes, setCrontabMinutes] = useState<string>("*");
	const [crontabHours, setCrontabHours] = useState<string>("*");
	const [crontabDaysOfMonth, setCrontabDaysOfMonth] = useState<string>("*");
	const [crontabMonthsOfYear, setCrontabMonthsOfYear] = useState<string>("*");
	const [crontabDaysOfWeek, setCrontabDaysOfWeek] = useState<string>("*");
	const [crontabTimezone, setCrontabTimezone] = useState<string>(Intl.DateTimeFormat().resolvedOptions().timeZone);

	// Parse incoming value on mount or when it changes
	useEffect(() => {
		if (value) {
			try {
				console.log("value", value);
				// Convert value to string first if it's not already
				const stringValue = typeof value === "string" ? value : JSON.stringify(value);

				if (!stringValue || !stringValue.trim()) {
					return;
				}

				const parsed: any = JSON.parse(stringValue);

				// Check if it's the new YAML-style format
				if (parsed.interval) {
					// New format: { interval: { every: 2, period: "minutes" } }
					setScheduleType("interval");
					setIntervalEvery(String(parsed.interval.every));
					setIntervalType(parsed.interval.period);
				} else if (parsed.cron) {
					// New format: { cron: "30 15 * * *", timezone: "UTC" }
					setScheduleType("crontab");
					const cronParts = parsed.cron.split(" ");
					if (cronParts.length === 5) {
						setCrontabMinutes(cronParts[0]);
						setCrontabHours(cronParts[1]);
						setCrontabDaysOfMonth(cronParts[2]);
						setCrontabMonthsOfYear(cronParts[3]);
						setCrontabDaysOfWeek(cronParts[4]);
					}
					setCrontabTimezone(parsed.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone);
				} else if (parsed.manual) {
					// New format: { manual: true }
					setScheduleType("none");
				} else if (parsed.schedule_type) {
					// Old format for backward compatibility
					setScheduleType(parsed.schedule_type || "interval");
					if (parsed.schedule_type === "interval") {
						setIntervalEvery(parsed.interval_every || "30");
						setIntervalType(parsed.interval_type || "minutes");
					} else if (parsed.schedule_type === "crontab") {
						setCrontabMinutes(parsed.crontab_minutes || "*");
						setCrontabHours(parsed.crontab_hours || "*");
						setCrontabDaysOfMonth(parsed.crontab_days_of_month || "*");
						setCrontabMonthsOfYear(parsed.crontab_months_of_year || "*");
						setCrontabDaysOfWeek(parsed.crontab_days_of_week || "*");
						setCrontabTimezone(parsed.crontab_timezone || Intl.DateTimeFormat().resolvedOptions().timeZone);
					}
				}
			} catch (error) {
				console.error("Failed to parse schedule value:", error);
			}
		}
	}, [value]);

	const getScheduleTypeLabel = () => {
		switch (scheduleType) {
			case "interval":
				return "Interval";
			case "crontab":
				return "Cron";
			case "none":
				return "Manual / Webhook Only";
			default:
				return "Select Schedule Type";
		}
	};

	const getScheduleDisplayText = () => {
		switch (scheduleType) {
			case "interval":
				return `Every ${intervalEvery} ${intervalType}`;
			case "crontab":
				return `Cron: ${crontabMinutes} ${crontabHours} ${crontabDaysOfMonth} ${crontabMonthsOfYear} ${crontabDaysOfWeek} (${crontabTimezone})`;
			case "none":
				return "Manual / Webhook Only";
			default:
				return "Not configured";
		}
	};

	const handleSaveSchedule = () => {
		let scheduleData: any = {};

		if (scheduleType === "interval") {
			// New YAML format: { interval: { every: 2, period: "minutes" } }
			scheduleData = {
				interval: {
					every: parseInt(intervalEvery) || 30,
					period: intervalType,
				},
			};
		} else if (scheduleType === "crontab") {
			// New YAML format: { cron: "30 15 * * *", timezone: "UTC" }
			const cronString = `${crontabMinutes} ${crontabHours} ${crontabDaysOfMonth} ${crontabMonthsOfYear} ${crontabDaysOfWeek}`;
			scheduleData = {
				cron: cronString,
				timezone: crontabTimezone,
			};
		} else if (scheduleType === "none") {
			// For manual/webhook only, we can send an empty object or a specific flag
			scheduleData = {
				manual: true,
			};
		}

		onChange(JSON.stringify(scheduleData));
		setShowModal(false);
	};

	return (
		<>
			<div className="github-input-container">
				<div className="p-3 border rounded" style={{ backgroundColor: "#f8f9fa", borderColor: "#e9ecef" }}>
					{/* Desktop layout */}
					<div className="d-flex align-items-center justify-content-between d-none d-sm-flex">
						<div className="d-flex align-items-center gap-3">
							{/* Clock icon */}
							<svg width="24" height="24" viewBox="0 0 24 24" fill="white" style={{ flexShrink: 0 }}>
								<path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z" />
							</svg>
							<div>
								<div className="fw-medium" style={{ fontSize: "0.95rem" }}>
									Schedule Configuration
								</div>
								<div className="text-muted small">{getScheduleDisplayText()}</div>
							</div>
						</div>
						<Button
							variant="primary"
							size="sm"
							onClick={() => setShowModal(true)}
							style={{
								display: "flex",
								alignItems: "center",
								gap: "6px",
								fontWeight: "500",
								padding: "6px 12px",
								borderRadius: "6px",
								fontSize: "0.875rem",
							}}>
							<i className="bi bi-pencil-square"></i>
							Edit Schedule
						</Button>
					</div>

					{/* Mobile layout */}
					<div className="d-flex d-sm-none flex-column">
						<div className="d-flex align-items-center gap-3 mb-3">
							{/* Clock icon */}
							<svg width="24" height="24" viewBox="0 0 24 24" fill="white" style={{ flexShrink: 0 }}>
								<path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z" />
							</svg>
							<div>
								<div className="fw-medium" style={{ fontSize: "0.95rem" }}>
									Schedule Configuration
								</div>
								<div className="text-muted small">{getScheduleDisplayText()}</div>
							</div>
						</div>
						<Button
							variant="primary"
							size="sm"
							onClick={() => setShowModal(true)}
							style={{
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								gap: "6px",
								fontWeight: "500",
								padding: "8px 16px",
								borderRadius: "6px",
								fontSize: "0.875rem",
							}}>
							<i className="bi bi-pencil-square"></i>
							Edit Schedule
						</Button>
					</div>
				</div>
			</div>

			{/* Schedule Configuration Modal */}
			<Modal show={showModal} onHide={() => setShowModal(false)} size="lg" centered>
				<Modal.Header closeButton style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.1)" }}>
					<Modal.Title>
						<i className="bi bi-clock-history me-2"></i>
						Configure Schedule
					</Modal.Title>
				</Modal.Header>
				<Modal.Body style={{ padding: "1.5rem" }}>
					{/* Schedule Type Selector */}
					<Form.Group className="mb-3">
						<Form.Label style={{ fontWeight: "500", fontSize: "0.95rem" }}>Schedule Type</Form.Label>
						<DropdownButton
							variant="secondary"
							title={getScheduleTypeLabel()}
							id="scheduleTypeDropdown"
							onSelect={(selected) => setScheduleType(selected as "interval" | "crontab" | "none")}>
							<Dropdown.Item eventKey="interval">Interval</Dropdown.Item>
							<Dropdown.Item eventKey="crontab">Cron</Dropdown.Item>
							<Dropdown.Item eventKey="none">Manual/Webhook Only</Dropdown.Item>
						</DropdownButton>
					</Form.Group>

					{/* Interval Schedule */}
					{scheduleType === "interval" && (
						<div
							style={{
								backgroundColor: "rgba(255, 255, 255, 0.02)",
								padding: "1.25rem",
								borderRadius: "8px",
								border: "1px solid rgba(255, 255, 255, 0.08)",
							}}>
							<Form.Group>
								<Form.Label style={{ fontWeight: "500", fontSize: "0.95rem" }}>
									<i className="bi bi-arrow-repeat me-2"></i>
									Interval Configuration
								</Form.Label>
								<div className="d-flex align-items-center gap-2">
									<span style={{ fontSize: "0.9rem" }}>Every</span>
									<Form.Control type="text" value={intervalEvery} onChange={(e) => setIntervalEvery(e.target.value)} style={{ width: "80px" }} />
									<DropdownButton
										variant="secondary"
										title={intervalType || "Select Type"}
										id="intervalTypeDropdown"
										onSelect={(selected) => setIntervalType(selected!)}>
										<Dropdown.Item eventKey="days">days</Dropdown.Item>
										<Dropdown.Item eventKey="hours">hours</Dropdown.Item>
										<Dropdown.Item eventKey="minutes">minutes</Dropdown.Item>
										<Dropdown.Item eventKey="seconds">seconds</Dropdown.Item>
										<Dropdown.Item eventKey="microseconds">microseconds</Dropdown.Item>
									</DropdownButton>
								</div>
								<Form.Text className="text-secondary d-block mt-2" style={{ fontSize: "0.85rem" }}>
									<i className="bi bi-info-circle me-1"></i>
									Schedule will run every{" "}
									<strong>
										{intervalEvery} {intervalType}
									</strong>
								</Form.Text>
							</Form.Group>
						</div>
					)}

					{/* Cron Schedule */}
					{scheduleType === "crontab" && (
						<div
							style={{
								backgroundColor: "rgba(255, 255, 255, 0.02)",
								padding: "0.85rem",
								borderRadius: "8px",
								border: "1px solid rgba(255, 255, 255, 0.08)",
							}}>
							<h6 style={{ fontWeight: "500", fontSize: "0.95rem", marginBottom: "0.6rem" }}>
								<i className="bi bi-calendar3 me-2"></i>
								Cron Expression
							</h6>
							<div className="row">
								{/* Minute */}
								<div className="col-md-6 mb-1">
									<Form.Group>
										<Form.Label style={{ fontSize: "0.9rem", fontWeight: "500" }}>Minute (m)</Form.Label>
										<Form.Control type="text" value={crontabMinutes} onChange={(e) => setCrontabMinutes(e.target.value)} placeholder="*" />
										<Form.Text className="text-secondary" style={{ fontSize: "0.8rem" }}>
											0-59 or *
										</Form.Text>
									</Form.Group>
								</div>

								{/* Hour */}
								<div className="col-md-6 mb-1">
									<Form.Group>
										<Form.Label style={{ fontSize: "0.9rem", fontWeight: "500" }}>Hour (h)</Form.Label>
										<Form.Control type="text" value={crontabHours} onChange={(e) => setCrontabHours(e.target.value)} placeholder="*" />
										<Form.Text className="text-secondary" style={{ fontSize: "0.8rem" }}>
											0-23 or *
										</Form.Text>
									</Form.Group>
								</div>

								{/* Day of Month */}
								<div className="col-md-6 mb-1">
									<Form.Group>
										<Form.Label style={{ fontSize: "0.9rem", fontWeight: "500" }}>Day of Month (dM)</Form.Label>
										<Form.Control type="text" value={crontabDaysOfMonth} onChange={(e) => setCrontabDaysOfMonth(e.target.value)} placeholder="*" />
										<Form.Text className="text-secondary" style={{ fontSize: "0.8rem" }}>
											1-31 or *
										</Form.Text>
									</Form.Group>
								</div>

								{/* Month of Year */}
								<div className="col-md-6 mb-1">
									<Form.Group>
										<Form.Label style={{ fontSize: "0.9rem", fontWeight: "500" }}>Month of Year (MY)</Form.Label>
										<Form.Control type="text" value={crontabMonthsOfYear} onChange={(e) => setCrontabMonthsOfYear(e.target.value)} placeholder="*" />
										<Form.Text className="text-secondary" style={{ fontSize: "0.8rem" }}>
											1-12 or *
										</Form.Text>
									</Form.Group>
								</div>

								{/* Day of Week */}
								<div className="col-md-6 mb-1">
									<Form.Group>
										<Form.Label style={{ fontSize: "0.9rem", fontWeight: "500" }}>Day of Week (d)</Form.Label>
										<Form.Control type="text" value={crontabDaysOfWeek} onChange={(e) => setCrontabDaysOfWeek(e.target.value)} placeholder="*" />
										<Form.Text className="text-secondary" style={{ fontSize: "0.8rem" }}>
											0-6 (Sun-Sat) or *
										</Form.Text>
									</Form.Group>
								</div>

								{/* Timezone */}
								<div className="col-md-6 mb-1">
									<Form.Group>
										<Form.Label style={{ fontSize: "0.9rem", fontWeight: "500" }}>Timezone</Form.Label>
										<DropdownButton
											variant="secondary"
											title={crontabTimezone || "Select Timezone"}
											id="timezoneDropdown"
											onSelect={(selected) => setCrontabTimezone(selected!)}
											style={{ width: "100%" }}>
											{timezones.map((timezone, index) => (
												<Dropdown.Item key={index} eventKey={timezone}>
													{timezone}
												</Dropdown.Item>
											))}
										</DropdownButton>
										<Form.Text className="text-secondary" style={{ fontSize: "0.8rem" }}>
											Select timezone for cron execution
										</Form.Text>
									</Form.Group>
								</div>
							</div>
							<div
								style={{
									marginTop: "0.5rem",
									padding: "0.5rem 0.65rem",
									backgroundColor: "rgba(13, 110, 253, 0.1)",
									borderRadius: "6px",
									border: "1px solid rgba(13, 110, 253, 0.2)",
								}}>
								<Form.Text className="text-secondary d-block" style={{ fontSize: "0.82rem" }}>
									<i className="bi bi-info-circle me-1"></i>
									<strong>Cron expression:</strong> {crontabMinutes} {crontabHours} {crontabDaysOfMonth} {crontabMonthsOfYear} {crontabDaysOfWeek} (
									{crontabTimezone})
								</Form.Text>
							</div>
						</div>
					)}

					{/* Manual/Webhook Only */}
					{scheduleType === "none" && (
						<div
							style={{
								backgroundColor: "rgba(13, 202, 240, 0.1)",
								padding: "1rem",
								borderRadius: "8px",
								border: "1px solid rgba(13, 202, 240, 0.2)",
							}}>
							<i className="bi bi-info-circle me-2"></i>
							This schedule will only run manually or via webhook trigger.
						</div>
					)}
				</Modal.Body>
				<Modal.Footer style={{ borderTop: "1px solid rgba(255, 255, 255, 0.1)" }}>
					<Button variant="secondary" onClick={() => setShowModal(false)}>
						Cancel
					</Button>
					<Button variant="primary" onClick={handleSaveSchedule}>
						Save Schedule
					</Button>
				</Modal.Footer>
			</Modal>
		</>
	);
};

export default ScheduleInput;
