import { createContext, useContext } from "react";

// Create the context for wizard modal
const WizardContext = createContext<
	| {
			triggerWizard: () => void;
	  }
	| undefined
>(undefined);

// Export a custom hook to use the WizardContext
export const useWizard = () => {
	const context = useContext(WizardContext);
	if (!context) {
		throw new Error("useWizard must be used within a WizardProvider");
	}
	return context;
};

export default WizardContext; 