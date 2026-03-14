export type DisplayPlan = "STARTER" | "PLUS" | "PRO";
export type AccessPlan = "starter" | "plus" | "pro" | "builder";

const VALID_PAID_PLANS = new Set(["plus", "pro"]);

const toPlanToken = (plan: unknown): string => String(plan || "").trim().toLowerCase();

export const normalizeAccessPlan = (plan: unknown): AccessPlan => {
	const token = toPlanToken(plan);
	if (token === "builder") return "builder";
	if (VALID_PAID_PLANS.has(token)) return token as AccessPlan;
	return "starter";
};

export const normalizeDisplayPlan = (plan: unknown): DisplayPlan => {
	const accessPlan = normalizeAccessPlan(plan);
	if (accessPlan === "plus") return "PLUS";
	if (accessPlan === "pro") return "PRO";
	return "STARTER";
};

export const persistUserPlan = (plan: unknown): { accessPlan: AccessPlan; displayPlan: DisplayPlan } => {
	const accessPlan = normalizeAccessPlan(plan);
	const displayPlan = normalizeDisplayPlan(plan);
	localStorage.setItem("plan_name", displayPlan);
	localStorage.setItem("plan_access", accessPlan);
	return { accessPlan, displayPlan };
};

export const getStoredAccessPlan = (): AccessPlan => {
	const storedAccess = localStorage.getItem("plan_access");
	if (storedAccess) return normalizeAccessPlan(storedAccess);
	// Backward compatibility for older sessions that only had plan_name.
	return normalizeAccessPlan(localStorage.getItem("plan_name"));
};

export const getStoredDisplayPlan = (): DisplayPlan => {
	const storedPlan = localStorage.getItem("plan_name");
	if (storedPlan) return normalizeDisplayPlan(storedPlan);
	return normalizeDisplayPlan(localStorage.getItem("plan_access"));
};

export const hasBuilderAccess = (): boolean => getStoredAccessPlan() === "builder";
