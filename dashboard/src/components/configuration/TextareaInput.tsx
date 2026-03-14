import React from "react";
import { Form } from "react-bootstrap";

interface TextareaInputProps {
	value: string;
	onChange: (value: string) => void;
	placeholder?: string;
	disabled?: boolean;
	required?: boolean;
	rows?: number;
}

const TextareaInput: React.FC<TextareaInputProps> = ({
	value,
	onChange,
	placeholder,
	disabled = false,
	required = false,
	rows = 4,
}) => {
	return (
		<Form.Control
			as="textarea"
			value={value || ""}
			onChange={(e) => onChange(e.target.value)}
			placeholder={placeholder}
			disabled={disabled}
			required={required}
			rows={rows}
		/>
	);
};

export default TextareaInput;
