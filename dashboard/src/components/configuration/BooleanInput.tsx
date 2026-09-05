import React from "react";
import { Form } from "react-bootstrap";

interface BooleanInputProps {
	value: string;
	onChange: (value: string) => void;
	label?: string;
	disabled?: boolean;
}

const isTruthy = (value: string) => {
	return value === "true" || value === "1";
};

const BooleanInput: React.FC<BooleanInputProps> = ({ value, onChange, label = "Enabled", disabled = false }) => {
	return (
		<Form.Check
			type="switch"
			id={`boolean-input-${label.replace(/\s+/g, "-").toLowerCase()}`}
			label={label}
			checked={isTruthy(value || "")}
			disabled={disabled}
			onChange={(e) => onChange(e.target.checked ? "true" : "false")}
		/>
	);
};

export default BooleanInput;
