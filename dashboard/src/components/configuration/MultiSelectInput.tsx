import React, { useMemo } from "react";
import { Form } from "react-bootstrap";

interface Option {
	name: string;
	key: string;
}

interface MultiSelectInputProps {
	value: string;
	onChange: (value: string) => void;
	options: Option[];
	disabled?: boolean;
}

const parseSelectedKeys = (value: string): string[] => {
	if (!value || !value.trim()) {
		return [];
	}

	const trimmed = value.trim();
	try {
		const parsed = JSON.parse(trimmed);
		if (Array.isArray(parsed)) {
			return parsed.map((item) => String(item));
		}
	} catch (error) {
		// Fallback to comma-separated legacy values.
	}

	return trimmed
		.split(",")
		.map((item) => item.trim())
		.filter((item) => item.length > 0);
};

const MultiSelectInput: React.FC<MultiSelectInputProps> = ({ value, onChange, options, disabled = false }) => {
	const selectedKeys = useMemo(() => parseSelectedKeys(value), [value]);

	const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
		const nextSelectedKeys = Array.from(event.target.selectedOptions).map((option) => option.value);
		onChange(JSON.stringify(nextSelectedKeys));
	};

	return (
		<Form.Select multiple value={selectedKeys} onChange={handleChange} disabled={disabled} style={{ minHeight: "130px" }}>
			{options.map((option) => (
				<option key={option.key} value={option.key}>
					{option.name}
				</option>
			))}
		</Form.Select>
	);
};

export default MultiSelectInput;
