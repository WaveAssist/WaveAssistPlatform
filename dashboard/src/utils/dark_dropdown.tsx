import React, { useState, useEffect } from "react";
import "./dark_dropdown.css";

interface DropdownProps {
	items: string[];
	keys?: string[];
	defaultText?: string;
	headerText: string;
	onItemSelect: (item: string, key: string) => void;
}

const Dropdown: React.FC<DropdownProps> = ({ items, keys = items, defaultText, headerText, onItemSelect }) => {
	const [selectedItem, setSelectedItem] = useState<string>(defaultText || items[0]);

	useEffect(() => {
		// Update the selected item when defaultText or items change
		if (defaultText) {
			setSelectedItem(defaultText);
		} else {
			setSelectedItem(items[0]);
		}
	}, [defaultText, items]);

	const handleItemClick = (item: string, key: string) => {
		setSelectedItem(item);
		onItemSelect(item, key);
	};

	return (
		<div className="dropdown">
			<button
				className="btn btn-outline-secondary me-4 px-3 dropdown-toggle"
				type="button"
				id="dropdownMenuButton2"
				data-bs-toggle="dropdown"
				aria-expanded="false">
				{selectedItem}
			</button>
			<ul className="dropdown-menu dropdown-menu-dark" aria-labelledby="dropdownMenuButton2">
				<li className="text-header-dropdown">{headerText}</li>
				<li>
					<hr className="dropdown-divider" />
				</li>
				{items.map((item, index) => (
					<li key={index}>
						<a
							className={`dropdown-item ${item === selectedItem ? "active" : ""}`}
							href="#"
							onClick={(e) => {
								e.preventDefault();
								handleItemClick(item, keys[index]);
							}}>
							{item}
						</a>
					</li>
				))}
			</ul>
		</div>
	);
};

export default Dropdown;
