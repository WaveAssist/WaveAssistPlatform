// types.ts
export interface Toast {
	show: boolean;
	message: string;
	variant: string;
}

export interface ToastContextType {
	toast: Toast;
	showToast: (message: string, variant?: string) => void;
	hideToast: () => void;
}

export interface GenericDict {
	[key: string]: any;
}

export interface NodeType {
	name: string;
	is_enabled: boolean;
	is_starting_node: boolean;
	schedule_type: string;
	crontab_minutes: string;
	crontab_hours: string;
	crontab_days_of_month: string;
	crontab_months_of_year: string;
	crontab_days_of_week: string;
	crontab_timezone: string;

	interval_every: string;
	interval_type: string;

	input_data_key_array: GenericDict[];
	output_data_key_array: GenericDict[];
	run_after_nodes_array: GenericDict[];
}
