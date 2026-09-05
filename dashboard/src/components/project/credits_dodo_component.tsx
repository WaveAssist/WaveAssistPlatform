import React from "react";
import { getBrand } from "../../config/branding";
import WaveAssistCreditsComponent from "./waveassist_credits_component";
import GitZoidBillingComponent from "./gitzoid_billing_component";

// Brand-aware billing route: GitZoid gets the trial→Pro page, WaveAssist the pay-as-you-go
// credits page. Branch outside the components so neither one's hooks run for the other brand.
const BillingRoute: React.FC = () => (getBrand().billingModel === "trial" ? <GitZoidBillingComponent /> : <WaveAssistCreditsComponent />);

export default BillingRoute;
