import React from "react";
import { Form } from "react-bootstrap";
import StockSelector from "./StockSelector";
import CommoditySelector from "./CommoditySelector";
import DropdownInput from "./DropdownInput";
import TextInput from "./TextInput";
import GitHubInput from "./GitHubInput";
import ScheduleInput from "./ScheduleInput";

interface Option {
	name: string;
	key: string;
}

interface InputConfig {
	key: string;
	type: string;
	options?: Option[];
	helper_message?: string;
	default_value?: string;
}

interface InputFactoryProps {
	inputConfig: InputConfig;
	value: string;
	onChange: (value: string) => void;
	selectResources?: (inputData: any) => void;
	selectedResources?: any;
	onRefresh?: () => void;
	isOptional?: boolean;
}

const InputFactory: React.FC<InputFactoryProps> = ({
	inputConfig,
	value,
	onChange,
	selectResources,
	selectedResources,
	onRefresh,
	isOptional = false,
}) => {
	const { key, type, options, helper_message } = inputConfig;

	// Render appropriate input component based on type
	const renderInput = () => {
		switch (type) {
			case "stock":
				return <StockSelector value={value} onChange={onChange} />;

			case "commodity":
				return <CommoditySelector value={value} onChange={onChange} />;

			case "schedule": //for testing. do not change.
				return <ScheduleInput value={value} onChange={onChange} />;

			case "select":
			case "dropdown":
				if (Array.isArray(options) && options.length > 0) {
					return <DropdownInput value={value} onChange={onChange} options={options} />;
				}
				// Fallback to text input if no options provided
				return <TextInput value={value} onChange={onChange} />;

			case "email":
				return <TextInput type="email" value={value} onChange={onChange} />;

			case "password":
				return <TextInput type="password" value={value} onChange={onChange} />;

			case "number":
				return <TextInput type="number" value={value} onChange={onChange} />;

			case "tel":
				return <TextInput type="tel" value={value} onChange={onChange} />;

			case "url":
				return <TextInput type="url" value={value} onChange={onChange} />;

			case "github":
				return (
					<GitHubInput
						value={value}
						selectResources={selectResources}
						selectedResources={selectedResources}
						inputData={inputConfig}
						onRefresh={onRefresh}
					/>
				);

			case "text":
			default:
				// Check if it has options (for backward compatibility with existing code)
				if (Array.isArray(options) && options.length > 0) {
					return <DropdownInput value={value} onChange={onChange} options={options} />;
				}
				return <TextInput value={value} onChange={onChange} />;
		}
	};

	return (
		<Form.Group className="mb-3">
			<Form.Label>
				{key}
				{isOptional && <span className="text-muted ms-1">(Optional)</span>}
			</Form.Label>
			{renderInput()}
			{helper_message && <Form.Text className="text-secondary">{helper_message}</Form.Text>}
		</Form.Group>
	);
};

export default InputFactory;
