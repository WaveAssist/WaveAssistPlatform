import React, { useState, useEffect } from "react";
import { Form, DropdownButton, Dropdown, Button, Modal } from "react-bootstrap";
import timezones from "../../utils/timezones.json";

interface ScheduleInputProps {
	value: string;
	onChange: (value: string) => void;
}

interface ScheduleData {
	schedule_type: "interval" | "crontab" | "none";
	interval_every?: string;
	interval_type?: string;
	crontab_minutes?: string;
	crontab_hours?: string;
	crontab_days_of_month?: string;
	crontab_months_of_year?: string;
	crontab_days_of_week?: string;
	crontab_timezone?: string;
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
				// Convert value to string first if it's not already
				const stringValue = typeof value === "string" ? value : JSON.stringify(value);

				if (!stringValue || !stringValue.trim()) {
					return;
				}

				const parsed: ScheduleData = JSON.parse(stringValue);
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
				return `Cron: ${crontabMinutes} ${crontabHours} ${crontabDaysOfMonth} ${crontabMonthsOfYear} ${crontabDaysOfWeek}`;
			case "none":
				return "Manual / Webhook Only";
			default:
				return "Not configured";
		}
	};

	const handleSaveSchedule = () => {
		const scheduleData: ScheduleData = {
			schedule_type: scheduleType,
		};

		if (scheduleType === "interval") {
			scheduleData.interval_every = intervalEvery;
			scheduleData.interval_type = intervalType;
		} else if (scheduleType === "crontab") {
			scheduleData.crontab_minutes = crontabMinutes;
			scheduleData.crontab_hours = crontabHours;
			scheduleData.crontab_days_of_month = crontabDaysOfMonth;
			scheduleData.crontab_months_of_year = crontabMonthsOfYear;
			scheduleData.crontab_days_of_week = crontabDaysOfWeek;
			scheduleData.crontab_timezone = crontabTimezone;
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
				<Modal.Header closeButton>
					<Modal.Title>Configure Schedule</Modal.Title>
				</Modal.Header>
				<Modal.Body>
					{/* Schedule Type Selector */}
					<Form.Group className="mb-3">
						<Form.Label>Schedule Type</Form.Label>
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
						<Form.Group className="mb-3">
							<Form.Label>Interval</Form.Label>
							<div className="d-flex align-items-center gap-2">
								<span>Every</span>
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
							<Form.Text className="text-secondary">
								Schedule will run every {intervalEvery} {intervalType}
							</Form.Text>
						</Form.Group>
					)}

					{/* Cron Schedule */}
					{scheduleType === "crontab" && (
						<div>
							<div className="row">
								{/* Minute */}
								<div className="col-md-6 mb-3">
									<Form.Group>
										<Form.Label>Minute (m)</Form.Label>
										<Form.Control type="text" value={crontabMinutes} onChange={(e) => setCrontabMinutes(e.target.value)} placeholder="*" />
										<Form.Text className="text-secondary">0-59 or *</Form.Text>
									</Form.Group>
								</div>

								{/* Hour */}
								<div className="col-md-6 mb-3">
									<Form.Group>
										<Form.Label>Hour (h)</Form.Label>
										<Form.Control type="text" value={crontabHours} onChange={(e) => setCrontabHours(e.target.value)} placeholder="*" />
										<Form.Text className="text-secondary">0-23 or *</Form.Text>
									</Form.Group>
								</div>

								{/* Day of Month */}
								<div className="col-md-6 mb-3">
									<Form.Group>
										<Form.Label>Day of Month (dM)</Form.Label>
										<Form.Control type="text" value={crontabDaysOfMonth} onChange={(e) => setCrontabDaysOfMonth(e.target.value)} placeholder="*" />
										<Form.Text className="text-secondary">1-31 or *</Form.Text>
									</Form.Group>
								</div>

								{/* Month of Year */}
								<div className="col-md-6 mb-3">
									<Form.Group>
										<Form.Label>Month of Year (MY)</Form.Label>
										<Form.Control type="text" value={crontabMonthsOfYear} onChange={(e) => setCrontabMonthsOfYear(e.target.value)} placeholder="*" />
										<Form.Text className="text-secondary">1-12 or *</Form.Text>
									</Form.Group>
								</div>

								{/* Day of Week */}
								<div className="col-md-6 mb-3">
									<Form.Group>
										<Form.Label>Day of Week (d)</Form.Label>
										<Form.Control type="text" value={crontabDaysOfWeek} onChange={(e) => setCrontabDaysOfWeek(e.target.value)} placeholder="*" />
										<Form.Text className="text-secondary">0-6 (Sun-Sat) or *</Form.Text>
									</Form.Group>
								</div>

								{/* Timezone */}
								<div className="col-md-6 mb-3">
									<Form.Group>
										<Form.Label>Timezone</Form.Label>
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
									</Form.Group>
								</div>
							</div>
							<Form.Text className="text-secondary">
								Cron expression: {crontabMinutes} {crontabHours} {crontabDaysOfMonth} {crontabMonthsOfYear} {crontabDaysOfWeek} ({crontabTimezone})
							</Form.Text>
						</div>
					)}

					{/* Manual/Webhook Only */}
					{scheduleType === "none" && (
						<div className="alert alert-info">
							<i className="bi bi-info-circle me-2"></i>
							This schedule will only run manually or via webhook trigger.
						</div>
					)}
				</Modal.Body>
				<Modal.Footer>
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
