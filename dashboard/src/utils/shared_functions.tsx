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
