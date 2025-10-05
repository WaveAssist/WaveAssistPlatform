import React, { useState, useRef, useEffect } from "react";
import { Form } from "react-bootstrap";
import { useToast } from "../../utils/toast_context";
import "./StockSelector.css";

interface Stock {
	_id: string;
	symbol: string;
	name: string;
	exchange: string;
	country: string;
	currency: string;
}

interface StockSelectorProps {
	value: string;
	onChange: (value: string) => void;
	placeholder?: string;
	maxSelected?: number;
}

const StockSelector: React.FC<StockSelectorProps> = ({ value, onChange, placeholder = "Search for your stocks...", maxSelected = 10 }) => {
	const { showToast } = useToast();
	const [stockSearchQuery, setStockSearchQuery] = useState("");
	const [stockSearchResults, setStockSearchResults] = useState<Stock[]>([]);
	const [stockSearchLoading, setStockSearchLoading] = useState(false);
	const [selectedStocks, setSelectedStocks] = useState<Stock[]>([]);
	const [stockSearchTimeout, setStockSearchTimeout] = useState<NodeJS.Timeout | null>(null);
	const [hasSearched, setHasSearched] = useState(false);
	const [detectedCountry, setDetectedCountry] = useState<string>("");
	const stockSearchAbortController = useRef<AbortController | null>(null);

	// Detect country from IP address on component mount
	useEffect(() => {
		const detectCountry = async () => {
			try {
				const response = await fetch("https://ipapi.co/json/");
				const data = await response.json();
				if (data.country_name) {
					setDetectedCountry(data.country_name);
				}
			} catch (error) {
				console.error("Failed to detect country from IP:", error);
				// Fallback to a default country or leave empty
			}
		};

		detectCountry();
	}, []);

	// Initialize selected stocks from value prop
	useEffect(() => {
		if (value && value.trim()) {
			try {
				// Check if value is JSON (new format) or CSV (old format)
				if (value.startsWith("[") && value.endsWith("]")) {
					// JSON format - parse as array of stock objects
					const parsedStocks = JSON.parse(value);
					if (Array.isArray(parsedStocks)) {
						setSelectedStocks(parsedStocks);
					}
				} else {
					// CSV format - parse as comma-separated symbols
					const symbols = value
						.split(",")
						.map((s) => s.trim())
						.filter((s) => s);
					if (symbols.length > 0) {
						// Convert symbols to basic stock objects
						// We'll create minimal stock objects with just the symbol
						const stockObjects = symbols.map((symbol) => ({
							_id: symbol, // Use symbol as ID for now
							symbol: symbol,
							name: symbol, // Fallback to symbol as name
							exchange: "Unknown",
							country: "Unknown",
							currency: "Unknown",
						}));
						setSelectedStocks(stockObjects);
					}
				}
			} catch (error) {
				console.error("Failed to parse stock value:", error);
				// If parsing fails, treat as empty selection
				setSelectedStocks([]);
			}
		} else {
			setSelectedStocks([]);
		}
	}, [value]);

	// Cleanup stock search timeout on unmount
	useEffect(() => {
		return () => {
			if (stockSearchTimeout) {
				clearTimeout(stockSearchTimeout);
			}
		};
	}, [stockSearchTimeout]);

	const searchStocks = async (query: string) => {
		if (!query.trim()) {
			setStockSearchResults([]);
			setHasSearched(false);
			return;
		}

		// Cancel previous request if it exists
		if (stockSearchAbortController.current) {
			stockSearchAbortController.current.abort();
		}

		// Create new abort controller for this request
		stockSearchAbortController.current = new AbortController();

		setStockSearchLoading(true);
		try {
			// Build URL with detected country parameter
			let url = `https://appsapi.waveassist.io/generic/search_stocks/${encodeURIComponent(query)}`;
			if (detectedCountry) {
				url += `?country=${encodeURIComponent(detectedCountry)}`;
			}

			const response = await fetch(url, {
				signal: stockSearchAbortController.current.signal,
			});
			const data = await response.json();

			if (data.status === "success" && data.data.stocks) {
				setStockSearchResults(data.data.stocks);
			} else {
				setStockSearchResults([]);
			}
			setHasSearched(true);
		} catch (error: any) {
			// Don't log error if it was aborted
			if (error.name !== "AbortError") {
				console.error("Stock search failed:", error);
				setStockSearchResults([]);
				setHasSearched(true);
			}
		} finally {
			setStockSearchLoading(false);
		}
	};

	const handleStockSearchChange = (query: string) => {
		setStockSearchQuery(query);

		// Clear existing timeout
		if (stockSearchTimeout) {
			clearTimeout(stockSearchTimeout);
		}

		// Set new timeout for debounced search
		const timeout = setTimeout(() => {
			searchStocks(query);
		}, 350); // 0.35 seconds delay

		setStockSearchTimeout(timeout);
	};

	const handleStockSelect = (stock: Stock) => {
		// Check if stock is already selected
		const isAlreadySelected = selectedStocks.some((s) => s._id === stock._id);
		if (!isAlreadySelected) {
			// Check if we already have maximum stocks selected
			if (selectedStocks.length >= maxSelected) {
				showToast(`Maximum ${maxSelected} stocks allowed`, "warning");
				return;
			}

			const newSelectedStocks = [...selectedStocks, stock];
			setSelectedStocks(newSelectedStocks);
			// Update value with selected stocks as JSON (for better data preservation)
			onChange(JSON.stringify(newSelectedStocks));
		}
		setStockSearchQuery("");
		setStockSearchResults([]);
	};

	const handleStockRemove = (stockId: string) => {
		const remainingStocks = selectedStocks.filter((s) => s._id !== stockId);
		setSelectedStocks(remainingStocks);
		// Update value with remaining stocks as JSON (for better data preservation)
		onChange(JSON.stringify(remainingStocks));
	};

	return (
		<div>
			{/* Stock Search Input */}
			<Form.Control type="text" placeholder={placeholder} value={stockSearchQuery} onChange={(e) => handleStockSearchChange(e.target.value)} />

			{/* Stock Search Results */}
			{stockSearchLoading && (
				<div className="mt-2">
					<span className="text-muted">Loading...</span>
				</div>
			)}

			{!stockSearchLoading && stockSearchQuery.trim() && stockSearchResults.length === 0 && hasSearched && (
				<div className="mt-2">
					<span className="text-muted">No results found for "{stockSearchQuery}"</span>
				</div>
			)}

			{stockSearchResults.length > 0 && (
				<div className="mt-2 stock-search-results-container p-2">
					{stockSearchResults.map((stock) => (
						<div key={stock._id} className="p-2 border-bottom stock-search-result" onClick={() => handleStockSelect(stock)}>
							<div className="fw-bold">{stock.symbol}</div>
							<div className="text-muted small">{stock.name}</div>
							<div className="text-muted small">
								{stock.exchange} • {stock.country} • {stock.currency}
							</div>
						</div>
					))}
				</div>
			)}

			{/* Selected Stocks */}
			<div className="mt-3">
				<small className="text-muted">
					Selected Stocks ({selectedStocks.length}/{maxSelected}):
				</small>
				{selectedStocks.length > 0 && (
					<div className="mt-2">
						{selectedStocks.map((stock) => (
							<span key={stock._id} className="badge stock-selected-badge">
								{stock.symbol} - {stock.name}
								<button type="button" className="btn-close" onClick={() => handleStockRemove(stock._id)}>
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

export default StockSelector;
