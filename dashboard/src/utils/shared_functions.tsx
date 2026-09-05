export const objectToCsvString = (data: any, key: string): string => {
	if (!Array.isArray(data)) {
		return "";
	}
	let csvString = "";
	data.forEach((item: any) => {
		if (item && typeof item === "object" && key in item) {
			csvString += item[key] + ",";
		} else {
			console.warn(`Key "${key}" not found in item:`, item);
		}
	});

	// Remove the trailing comma
	csvString = csvString.replace(/,\s*$/, "");
	return csvString;
};

export const downloadFile = (data: string, filename: string, mimeType: string) => {
	const blob = new Blob([data], { type: mimeType });
	const url = window.URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.style.display = "none";
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	window.URL.revokeObjectURL(url);
	document.body.removeChild(a);
};

/**
 * Converts a value to string format.
 * If value is an object or array, it will be JSON stringified.
 * If value is already a string, it will be returned as is.
 *
 * @param value - The value to convert to string
 * @returns The string representation of the value
 */
export const convertToString = (value: any): string => {
	if (value === null || value === undefined) {
		return "";
	}

	if (typeof value === "string") {
		return value;
	}

	if (typeof value === "object") {
		return JSON.stringify(value);
	}

	return String(value);
};

/**
 * Determines the data type for API calls.
 * First converts the value to string, then checks if it's valid JSON.
 *
 * @param value - The value to check (can be object, string, array, etc.)
 * @returns "json" if the value is a valid JSON object/array, "string" otherwise
 */
export const determineDataType = (value: any): "json" | "string" => {
	// Convert to string first to ensure consistent handling
	const stringValue = convertToString(value);

	// Empty strings are just strings
	if (!stringValue || stringValue.trim() === "") {
		return "string";
	}

	// Check if the string value starts with JSON indicators and is valid JSON
	const trimmedValue = stringValue.trim();
	if (trimmedValue.startsWith("[") || trimmedValue.startsWith("{")) {
		try {
			JSON.parse(trimmedValue);
			return "json";
		} catch {
			// If it looks like JSON but isn't valid, treat as string
			return "string";
		}
	}

	return "string";
};
