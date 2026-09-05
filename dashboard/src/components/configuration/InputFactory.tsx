import React from "react";
import { Form } from "react-bootstrap";
import StockSelector from "./StockSelector";
import CommoditySelector from "./CommoditySelector";
import CryptoSelector from "./CryptoSelector";
import DropdownInput from "./DropdownInput";
import TextInput from "./TextInput";
import TextareaInput from "./TextareaInput";
import BooleanInput from "./BooleanInput";
import MultiSelectInput from "./MultiSelectInput";
import ListInput from "./ListInput";
import SecretInput from "./SecretInput";
import ClickUpInput from "./ClickUpInput";
import ScheduleInput from "./ScheduleInput";
import ProviderInput from "./ProviderInput";
import RepoGroupsInput from "./RepoGroupsInput";
import { PROVIDER_CONFIGS } from "./providerConfigs";

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
	display_name?: string;
	placeholder?: string;
	max_items?: number;
	max_groups?: number;
	depends_on?: string;
	label?: string;
}

interface InputFactoryProps {
	inputConfig: InputConfig;
	value: string;
	onChange: (value: string) => void;
	selectResources?: (inputData: any) => void;
	selectedResources?: any;
	// Selected resources of the input named by this input's `depends_on` (e.g. the github repos that a
	// `repo_groups` input groups). Resolved by the parent so the group builder knows the repo list.
	dependsOnResources?: Array<{ id?: string; name?: string } | string>;
	onRefresh?: () => void;
	isOptional?: boolean;
	highlightSelectResources?: boolean;
}

const InputFactory: React.FC<InputFactoryProps> = ({
	inputConfig,
	value,
	onChange,
	selectResources,
	selectedResources,
	dependsOnResources,
	onRefresh,
	isOptional = false,
	highlightSelectResources = false,
}) => {
	const { key, type, options, helper_message, display_name, placeholder, max_items, max_groups, label } = inputConfig;

	// Render appropriate input component based on type
	const renderInput = () => {
		switch (type) {
			case "stock":
				return <StockSelector value={value} onChange={onChange} />;

			case "crypto":
				return <CryptoSelector value={value} onChange={onChange} />;

			case "commodity":
				return <CommoditySelector value={value} onChange={onChange} />;

			case "schedule":
				return <ScheduleInput value={value} onChange={onChange} options={options} />;

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

			case "secret":
				return <SecretInput value={value} onChange={onChange} placeholder={placeholder} />;

			case "number":
				return <TextInput type="number" value={value} onChange={onChange} />;

			case "tel":
				return <TextInput type="tel" value={value} onChange={onChange} />;

			case "url":
				return <TextInput type="url" value={value} onChange={onChange} />;

			case "textarea":
				return <TextareaInput value={value} onChange={onChange} placeholder={placeholder} />;

			case "boolean":
			case "checkbox":
			case "toggle":
				return <BooleanInput value={value} onChange={onChange} label={label || display_name || key} />;

			case "multiselect":
			case "multi_select":
				if (Array.isArray(options) && options.length > 0) {
					return <MultiSelectInput value={value} onChange={onChange} options={options} />;
				}
				return <TextInput value={value} onChange={onChange} placeholder={placeholder} />;

			case "list":
			case "chips":
				return <ListInput value={value} onChange={onChange} placeholder={placeholder} maxItems={max_items} />;

			case "repo_groups":
				return (
					<RepoGroupsInput
						value={value}
						onChange={onChange}
						availableRepos={dependsOnResources}
						maxGroups={max_groups}
					/>
				);

			case "clickup":
				return (
					<ClickUpInput
						value={value}
						selectResources={selectResources}
						inputData={inputConfig}
						onRefresh={onRefresh}
						highlightSelectResources={highlightSelectResources}
					/>
				);

			case "text":
			default:
				if (PROVIDER_CONFIGS[type]) {
					return (
						<ProviderInput
							config={PROVIDER_CONFIGS[type]}
							value={value}
							onChange={onChange}
							selectResources={selectResources}
							selectedResources={selectedResources}
							inputData={inputConfig}
							onRefresh={onRefresh}
							highlightSelectResources={highlightSelectResources}
						/>
					);
				}
				if (Array.isArray(options) && options.length > 0) {
					return <DropdownInput value={value} onChange={onChange} options={options} />;
				}
				return <TextInput value={value} onChange={onChange} placeholder={placeholder} />;
		}
	};

	return (
		<Form.Group className="mb-4">
			<Form.Label className="mb-2 d-block">
				{display_name || key}
				{!isOptional && <span style={{ color: "#ff4444", marginLeft: "4px" }}>*</span>}
				{isOptional && <span className="text-muted ms-1">(Optional)</span>}
			</Form.Label>
			<div className="mb-1">{renderInput()}</div>
			{helper_message && (
				<Form.Text className="text-secondary d-block mt-1" style={{ fontSize: "0.8rem" }}>
					{helper_message}
				</Form.Text>
			)}
		</Form.Group>
	);
};

export default InputFactory;
