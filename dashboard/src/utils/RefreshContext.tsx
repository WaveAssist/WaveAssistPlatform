import { createContext, useContext } from "react";

// Create the context outside of the Layout component
const RefreshContext = createContext<
	| {
			shouldRefresh: boolean;
			triggerRefresh: () => void;
	  }
	| undefined
>(undefined);

// Export a custom hook to use the RefreshContext
export const useRefresh = () => {
	const context = useContext(RefreshContext);
	if (!context) {
		throw new Error("useRefresh must be used within a RefreshProvider");
	}
	return context;
};

export default RefreshContext;
