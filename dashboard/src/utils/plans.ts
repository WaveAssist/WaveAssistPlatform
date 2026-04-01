export interface PlanOption {
	key: string;
	label: string;
	price: number;
	credits: number;
	features: string[];
	recommended?: boolean;
}

export const PLANS: PlanOption[] = [
	{
		key: "plus",
		label: "Plus",
		price: 9.99,
		credits: 10,
		features: ["$10 credits/month", "Unlimited runs", "Email support"],
	},
	{
		key: "pro",
		label: "Pro",
		price: 19.99,
		credits: 25,
		features: ["$25 credits/month", "Unlimited runs", "Priority support"],
		recommended: true,
	},
];
