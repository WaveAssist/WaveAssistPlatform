import React from "react";
import { Form } from "react-bootstrap";

interface Option {
	name: string;
	key: string;
}

interface DropdownInputProps {
	value: string;
	onChange: (value: string) => void;
	options: Option[];
	placeholder?: string;
	disabled?: boolean;
}

const DropdownInput: React.FC<DropdownInputProps> = ({ value, onChange, options, placeholder = "Select an option...", disabled = false }) => {
	return (
		<Form.Select value={value || options[0]?.key || ""} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
			{placeholder && (
				<option value="" disabled>
					{placeholder}
				</option>
			)}
			{options.map((option, index) => (
				<option key={index} value={option.key}>
					{option.name}
				</option>
			))}
		</Form.Select>
	);
};

export default DropdownInput;
