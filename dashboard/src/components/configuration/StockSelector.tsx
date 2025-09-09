import React, { useState, useRef, useEffect } from "react";
import { Form, Spinner } from "react-bootstrap";
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

const StockSelector: React.FC<StockSelectorProps> = ({ value, onChange, placeholder = "Search for stocks...", maxSelected = 5 }) => {
	const { showToast } = useToast();
	const [stockSearchQuery, setStockSearchQuery] = useState("");
	const [stockSearchResults, setStockSearchResults] = useState<Stock[]>([]);
	const [stockSearchLoading, setStockSearchLoading] = useState(false);
	const [selectedStocks, setSelectedStocks] = useState<Stock[]>([]);
	const [stockSearchTimeout, setStockSearchTimeout] = useState<NodeJS.Timeout | null>(null);
	const stockSearchAbortController = useRef<AbortController | null>(null);

	// Initialize selected stocks from value prop
	useEffect(() => {
		if (value && value.trim()) {
			// Parse CSV value to get stock symbols
			// Note: We can't reconstruct full stock objects from just symbols
			// This is a limitation - we'd need to store more data or refetch
			// For now, we'll work with the symbols as strings
			// TODO: Implement proper stock reconstruction from stored data
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
			const response = await fetch(`https://appsapi.waveassist.io/generic/search_stocks/${encodeURIComponent(query)}`, {
				signal: stockSearchAbortController.current.signal,
			});
			const data = await response.json();

			if (data.status === "success" && data.data.stocks) {
				setStockSearchResults(data.data.stocks);
			} else {
				setStockSearchResults([]);
			}
		} catch (error: any) {
			// Don't log error if it was aborted
			if (error.name !== "AbortError") {
				console.error("Stock search failed:", error);
				setStockSearchResults([]);
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
			// Update value with selected stocks as CSV
			const stockSymbols = newSelectedStocks.map((s) => s.symbol).join(",");
			onChange(stockSymbols);
		}
		setStockSearchQuery("");
		setStockSearchResults([]);
	};

	const handleStockRemove = (stockId: string) => {
		const remainingStocks = selectedStocks.filter((s) => s._id !== stockId);
		setSelectedStocks(remainingStocks);
		// Update value with remaining stocks as CSV
		const stockSymbols = remainingStocks.map((s) => s.symbol).join(",");
		onChange(stockSymbols);
	};

	return (
		<div>
			{/* Stock Search Input */}
			<Form.Control type="text" placeholder={placeholder} value={stockSearchQuery} onChange={(e) => handleStockSearchChange(e.target.value)} />

			{/* Stock Search Results */}
			{stockSearchLoading && (
				<div className="mt-2">
					<Spinner animation="border" size="sm" /> <span className="text-muted">Loading...</span>
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
