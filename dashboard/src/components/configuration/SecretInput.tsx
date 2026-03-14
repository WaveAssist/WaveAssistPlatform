import React, { useState } from "react";
import { Form, InputGroup, Button } from "react-bootstrap";

interface SecretInputProps {
	value: string;
	onChange: (value: string) => void;
	placeholder?: string;
	disabled?: boolean;
}

const SecretInput: React.FC<SecretInputProps> = ({ value, onChange, placeholder = "Enter secret...", disabled = false }) => {
	const [isVisible, setIsVisible] = useState(false);

	return (
		<InputGroup>
			<Form.Control
				type={isVisible ? "text" : "password"}
				value={value || ""}
				onChange={(e) => onChange(e.target.value)}
				placeholder={placeholder}
				autoComplete="off"
				disabled={disabled}
			/>
			<Button variant="outline-secondary" onClick={() => setIsVisible((prev) => !prev)} disabled={disabled}>
				{isVisible ? "Hide" : "Show"}
			</Button>
		</InputGroup>
	);
};

export default SecretInput;
