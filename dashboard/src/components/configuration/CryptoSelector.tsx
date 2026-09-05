import React, { useState, useRef, useEffect } from "react";
import { Form } from "react-bootstrap";
import { useToast } from "../../utils/toast_context";
import "./StockSelector.css";

interface CryptoAsset {
	_id: string;
	Symbol: string;
	Name?: string;
	Description?: string;
	FromCurrency?: string;
	ToCurrency?: string;
	Currency?: string;
	CompanyType?: string;
}

interface CryptoSelectorProps {
	value: string;
	onChange: (value: string) => void;
	placeholder?: string;
	maxSelected?: number;
}

const CryptoSelector: React.FC<CryptoSelectorProps> = ({ value, onChange, placeholder = "Search for crypto...", maxSelected = 10 }) => {
	const { showToast } = useToast();
	const [cryptoSearchQuery, setCryptoSearchQuery] = useState("");
	const [cryptoSearchResults, setCryptoSearchResults] = useState<CryptoAsset[]>([]);
	const [cryptoSearchLoading, setCryptoSearchLoading] = useState(false);
	const [selectedCryptos, setSelectedCryptos] = useState<CryptoAsset[]>([]);
	const [cryptoSearchTimeout, setCryptoSearchTimeout] = useState<NodeJS.Timeout | null>(null);
	const [hasSearched, setHasSearched] = useState(false);
	const cryptoSearchAbortController = useRef<AbortController | null>(null);

	// Initialize selected cryptos from value prop
	useEffect(() => {
		if (value) {
			try {
				const stringValue = typeof value === "string" ? value : JSON.stringify(value);

				if (!stringValue || !stringValue.trim()) {
					setSelectedCryptos([]);
					return;
				}

				const trimmedValue = stringValue.trim();

				// Support JSON array (preferred) and CSV of symbols (legacy)
				if (trimmedValue.startsWith("[") && trimmedValue.endsWith("]")) {
					const parsed = JSON.parse(trimmedValue);
					if (Array.isArray(parsed)) {
						setSelectedCryptos(parsed);
					}
				} else {
					const symbols = trimmedValue
						.split(",")
						.map((s) => s.trim())
						.filter((s) => s);
					if (symbols.length > 0) {
						const cryptoObjects = symbols.map((symbol) => ({
							_id: symbol,
							Symbol: symbol,
							Name: symbol,
						}));
						setSelectedCryptos(cryptoObjects);
					}
				}
			} catch (error) {
				console.error("Failed to parse crypto value:", error);
				setSelectedCryptos([]);
			}
		} else {
			setSelectedCryptos([]);
		}
	}, [value]);

	// Cleanup timeout on unmount
	useEffect(() => {
		return () => {
			if (cryptoSearchTimeout) {
				clearTimeout(cryptoSearchTimeout);
			}
		};
	}, [cryptoSearchTimeout]);

	const searchCryptos = async (query: string) => {
		if (!query.trim()) {
			setCryptoSearchResults([]);
			setHasSearched(false);
			return;
		}

		// Cancel previous request
		if (cryptoSearchAbortController.current) {
			cryptoSearchAbortController.current.abort();
		}

		cryptoSearchAbortController.current = new AbortController();
		setCryptoSearchLoading(true);
		try {
			const url = `https://appsapi.waveassist.io/generic/search_crypto/${encodeURIComponent(query)}`;
			const response = await fetch(url, {
				signal: cryptoSearchAbortController.current.signal,
			});
			const data = await response.json();

			if (data.status === "success" && data.data && data.data.crypto) {
				setCryptoSearchResults(data.data.crypto);
			} else {
				setCryptoSearchResults([]);
			}
			setHasSearched(true);
		} catch (error: any) {
			if (error.name !== "AbortError") {
				console.error("Crypto search failed:", error);
				setCryptoSearchResults([]);
				setHasSearched(true);
			}
		} finally {
			setCryptoSearchLoading(false);
		}
	};

	const handleCryptoSearchChange = (query: string) => {
		setCryptoSearchQuery(query);
		if (cryptoSearchTimeout) {
			clearTimeout(cryptoSearchTimeout);
		}
		const timeout = setTimeout(() => {
			searchCryptos(query);
		}, 350);
		setCryptoSearchTimeout(timeout);
	};

	const handleCryptoSelect = (crypto: CryptoAsset) => {
		const isAlreadySelected = selectedCryptos.some((c) => c._id === crypto._id);
		if (!isAlreadySelected) {
			if (selectedCryptos.length >= maxSelected) {
				showToast(`Maximum ${maxSelected} cryptos allowed`, "warning");
				return;
			}

			const newSelected = [...selectedCryptos, crypto];
			setSelectedCryptos(newSelected);
			onChange(JSON.stringify(newSelected));
		}
		setCryptoSearchQuery("");
		setCryptoSearchResults([]);
	};

	const handleCryptoRemove = (cryptoId: string) => {
		const remaining = selectedCryptos.filter((c) => c._id !== cryptoId);
		setSelectedCryptos(remaining);
		onChange(JSON.stringify(remaining));
	};

	return (
		<div>
			{/* Crypto Search Input */}
			<Form.Control type="text" placeholder={placeholder} value={cryptoSearchQuery} onChange={(e) => handleCryptoSearchChange(e.target.value)} />

			{/* Crypto Search Results */}
			{cryptoSearchLoading && (
				<div className="mt-2">
					<span className="text-muted">Loading...</span>
				</div>
			)}

			{!cryptoSearchLoading && cryptoSearchQuery.trim() && cryptoSearchResults.length === 0 && hasSearched && (
				<div className="mt-2">
					<span className="text-muted">No results found for "{cryptoSearchQuery}"</span>
				</div>
			)}

			{cryptoSearchResults.length > 0 && (
				<div className="mt-2 stock-search-results-container p-2">
					{cryptoSearchResults.map((crypto) => (
						<div key={crypto._id} className="p-2 border-bottom stock-search-result" onClick={() => handleCryptoSelect(crypto)}>
							<div className="fw-bold">{crypto.Symbol || crypto.FromCurrency}</div>
							{(crypto.Name || crypto.Description) && (
								<div className="text-muted small">{crypto.Name || crypto.Description}</div>
							)}
							<div className="text-muted small">
								{crypto.CompanyType || "CRYPTOCURRENCY"}
								{crypto.Currency ? ` • ${crypto.Currency}` : ""}
							</div>
						</div>
					))}
				</div>
			)}

			{/* Selected Cryptos */}
			<div className="mt-3">
				<small className="text-muted">Selected Crypto ({selectedCryptos.length}/{maxSelected}):</small>
				{selectedCryptos.length > 0 && (
					<div className="mt-2">
						{selectedCryptos.map((crypto) => (
							<span key={crypto._id} className="badge stock-selected-badge">
								{crypto.Symbol || crypto.FromCurrency} - {crypto.Name || crypto.Description || ""}
								<button type="button" className="btn-close" onClick={() => handleCryptoRemove(crypto._id)}>
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

export default CryptoSelector;


