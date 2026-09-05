import React from "react";
import { Form } from "react-bootstrap";

interface TextInputProps {
	value: string;
	onChange: (value: string) => void;
	type?: "text" | "email" | "password" | "number" | "tel" | "url";
	placeholder?: string;
	disabled?: boolean;
	required?: boolean;
	min?: number;
	max?: number;
	step?: number;
}

const TextInput: React.FC<TextInputProps> = ({
	value,
	onChange,
	type = "text",
	placeholder,
	disabled = false,
	required = false,
	min,
	max,
	step,
}) => {
	return (
		<Form.Control
			type={type}
			value={value || ""}
			onChange={(e) => onChange(e.target.value)}
			placeholder={placeholder}
			disabled={disabled}
			required={required}
			min={min}
			max={max}
			step={step}
		/>
	);
};

export default TextInput;

