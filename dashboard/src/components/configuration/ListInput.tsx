import React, { useMemo, useState } from "react";
import { Form, Button, InputGroup } from "react-bootstrap";

interface ListInputProps {
	value: string;
	onChange: (value: string) => void;
	placeholder?: string;
	maxItems?: number;
	disabled?: boolean;
}

const parseItems = (value: string): string[] => {
	if (!value || !value.trim()) {
		return [];
	}

	const trimmed = value.trim();
	try {
		const parsed = JSON.parse(trimmed);
		if (Array.isArray(parsed)) {
			return parsed.map((item) => String(item).trim()).filter((item) => item.length > 0);
		}
	} catch (error) {
		// Fallback to comma/newline-separated legacy values.
	}

	return trimmed
		.split(/[\n,]/)
		.map((item) => item.trim())
		.filter((item) => item.length > 0);
};

const ListInput: React.FC<ListInputProps> = ({
	value,
	onChange,
	placeholder = "Type an item and press Enter",
	maxItems = 100,
	disabled = false,
}) => {
	const [draft, setDraft] = useState("");
	const items = useMemo(() => parseItems(value), [value]);

	const saveItems = (nextItems: string[]) => {
		onChange(JSON.stringify(nextItems));
	};

	const handleAdd = () => {
		const normalized = draft.trim();
		if (!normalized) {
			return;
		}
		if (items.includes(normalized)) {
			setDraft("");
			return;
		}
		if (items.length >= maxItems) {
			return;
		}
		saveItems([...items, normalized]);
		setDraft("");
	};

	const handleRemove = (item: string) => {
		saveItems(items.filter((existing) => existing !== item));
	};

	return (
		<div>
			<InputGroup>
				<Form.Control
					type="text"
					value={draft}
					placeholder={placeholder}
					disabled={disabled}
					onChange={(e) => setDraft(e.target.value)}
					onKeyDown={(e) => {
						if (e.key === "Enter") {
							e.preventDefault();
							handleAdd();
						}
					}}
				/>
				<Button variant="outline-secondary" onClick={handleAdd} disabled={disabled || !draft.trim() || items.length >= maxItems}>
					Add
				</Button>
			</InputGroup>

			<div className="mt-2 d-flex flex-wrap gap-2">
				{items.map((item) => (
					<span key={item} className="badge bg-secondary d-inline-flex align-items-center">
						{item}
						<button
							type="button"
							className="btn-close btn-close-white ms-2"
							onClick={() => handleRemove(item)}
							aria-label={`Remove ${item}`}
							style={{ fontSize: "0.6rem" }}
						/>
					</span>
				))}
			</div>
		</div>
	);
};

export default ListInput;
