import React, { useState, useRef, useEffect } from "react";
import { Form } from "react-bootstrap";
import { useToast } from "../../utils/toast_context";
import "./StockSelector.css"; // Reuse the same CSS styles

interface Commodity {
	_id: string;
	yfinance_symbol: string;
	name: string;
	type: string;
	currency: string;
}

interface CommoditySelectorProps {
	value: string;
	onChange: (value: string) => void;
	placeholder?: string;
	maxSelected?: number;
}

const CommoditySelector: React.FC<CommoditySelectorProps> = ({ value, onChange, placeholder = "Search for commodities...", maxSelected = 5 }) => {
	const { showToast } = useToast();
	const [commoditySearchQuery, setCommoditySearchQuery] = useState("");
	const [commoditySearchResults, setCommoditySearchResults] = useState<Commodity[]>([]);
	const [commoditySearchLoading, setCommoditySearchLoading] = useState(false);
	const [selectedCommodities, setSelectedCommodities] = useState<Commodity[]>([]);
	const [commoditySearchTimeout, setCommoditySearchTimeout] = useState<NodeJS.Timeout | null>(null);
	const [hasSearched, setHasSearched] = useState(false);
	const commoditySearchAbortController = useRef<AbortController | null>(null);

	// Initialize selected commodities from value prop
	useEffect(() => {
		if (value && value.trim()) {
			try {
				// Parse JSON value to get commodity objects
				const parsedCommodities = JSON.parse(value);
				if (Array.isArray(parsedCommodities)) {
					setSelectedCommodities(parsedCommodities);
				}
			} catch (error) {
				console.error("Failed to parse commodity value:", error);
				// If parsing fails, treat as empty selection
				setSelectedCommodities([]);
			}
		}
	}, [value]);

	// Cleanup commodity search timeout on unmount
	useEffect(() => {
		return () => {
			if (commoditySearchTimeout) {
				clearTimeout(commoditySearchTimeout);
			}
		};
	}, [commoditySearchTimeout]);

	const searchCommodities = async (query: string) => {
		if (!query.trim()) {
			setCommoditySearchResults([]);
			setHasSearched(false);
			return;
		}

		// Cancel previous request if it exists
		if (commoditySearchAbortController.current) {
			commoditySearchAbortController.current.abort();
		}

		// Create new abort controller for this request
		commoditySearchAbortController.current = new AbortController();

		setCommoditySearchLoading(true);
		try {
			// Build URL for commodity search (no country parameter needed)
			const url = `https://appsapi.waveassist.io/generic/search_commodities/${encodeURIComponent(query)}`;

			const response = await fetch(url, {
				signal: commoditySearchAbortController.current.signal,
			});
			const data = await response.json();

			if (data.status === "success" && data.data.commodities) {
				setCommoditySearchResults(data.data.commodities);
			} else {
				setCommoditySearchResults([]);
			}
			setHasSearched(true);
		} catch (error: any) {
			// Don't log error if it was aborted
			if (error.name !== "AbortError") {
				console.error("Commodity search failed:", error);
				setCommoditySearchResults([]);
				setHasSearched(true);
			}
		} finally {
			setCommoditySearchLoading(false);
		}
	};

	const handleCommoditySearchChange = (query: string) => {
		setCommoditySearchQuery(query);

		// Clear existing timeout
		if (commoditySearchTimeout) {
			clearTimeout(commoditySearchTimeout);
		}

		// Set new timeout for debounced search
		const timeout = setTimeout(() => {
			searchCommodities(query);
		}, 350); // 0.35 seconds delay

		setCommoditySearchTimeout(timeout);
	};

	const handleCommoditySelect = (commodity: Commodity) => {
		// Check if commodity is already selected
		const isAlreadySelected = selectedCommodities.some((c) => c._id === commodity._id);
		if (!isAlreadySelected) {
			// Check if we already have maximum commodities selected
			if (selectedCommodities.length >= maxSelected) {
				showToast(`Maximum ${maxSelected} commodities allowed`, "warning");
				return;
			}

			const newSelectedCommodities = [...selectedCommodities, commodity];
			setSelectedCommodities(newSelectedCommodities);
			// Update value with selected commodities as JSON
			onChange(JSON.stringify(newSelectedCommodities));
		}
		setCommoditySearchQuery("");
		setCommoditySearchResults([]);
	};

	const handleCommodityRemove = (commodityId: string) => {
		const remainingCommodities = selectedCommodities.filter((c) => c._id !== commodityId);
		setSelectedCommodities(remainingCommodities);
		// Update value with remaining commodities as JSON
		onChange(JSON.stringify(remainingCommodities));
	};

	return (
		<div>
			{/* Commodity Search Input */}
			<Form.Control
				type="text"
				placeholder={placeholder}
				value={commoditySearchQuery}
				onChange={(e) => handleCommoditySearchChange(e.target.value)}
			/>

			{/* Commodity Search Results */}
			{commoditySearchLoading && (
				<div className="mt-2">
					<span className="text-muted">Loading...</span>
				</div>
			)}

			{!commoditySearchLoading && commoditySearchQuery.trim() && commoditySearchResults.length === 0 && hasSearched && (
				<div className="mt-2">
					<span className="text-muted">No results found for "{commoditySearchQuery}"</span>
				</div>
			)}

			{commoditySearchResults.length > 0 && (
				<div className="mt-2 stock-search-results-container p-2">
					{commoditySearchResults.map((commodity) => (
						<div key={commodity._id} className="p-2 border-bottom stock-search-result" onClick={() => handleCommoditySelect(commodity)}>
							<div className="fw-bold">{commodity.name}</div>
							<div className="text-muted small">
								{commodity.type} • {commodity.currency}
							</div>
						</div>
					))}
				</div>
			)}

			{/* Selected Commodities */}
			<div className="mt-3">
				<small className="text-muted">
					Selected Commodities ({selectedCommodities.length}/{maxSelected}):
				</small>
				{selectedCommodities.length > 0 && (
					<div className="mt-2">
						{selectedCommodities.map((commodity) => (
							<span key={commodity._id} className="badge stock-selected-badge">
								{commodity.name} ({commodity.type})
								<button type="button" className="btn-close" onClick={() => handleCommodityRemove(commodity._id)}>
									×
								</button>
							</span>
						))}
					</div>
				)}
			</div>
		</div>
	);
};

export default CommoditySelector;
