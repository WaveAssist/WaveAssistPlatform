import { useRef } from "react";
import { useToast } from "../utils/toast_context";

type DodoSdk = {
	Initialize: (config: {
		mode: "test" | "live";
		displayType: "overlay";
		onEvent: (event: { event_type?: string; data?: { message?: string } }) => void;
	}) => void;
	Checkout: {
		open: (args: { checkoutUrl: string }) => void;
	};
};

const DODO_CHECKOUT_SCRIPT =
	import.meta.env.VITE_DODO_CHECKOUT_SCRIPT ||
	"https://cdn.jsdelivr.net/npm/dodopayments-checkout@latest/dist/index.js";
const DODO_MODE = (import.meta.env.VITE_DODO_MODE || "test") as "test" | "live";

const loadDodoCheckoutScript = async (): Promise<void> => {
	if ((window as any).DodoPayments || (window as any).DodoPaymentsCheckout?.DodoPayments) return;
	await new Promise<void>((resolve, reject) => {
		const existingScript = document.querySelector(`script[src="${DODO_CHECKOUT_SCRIPT}"]`);
		if (existingScript) {
			existingScript.addEventListener("load", () => resolve(), { once: true });
			existingScript.addEventListener("error", () => reject(new Error("DoDo SDK load failed")), { once: true });
			return;
		}
		const script = document.createElement("script");
		script.src = DODO_CHECKOUT_SCRIPT;
		script.async = true;
		script.onload = () => resolve();
		script.onerror = () => reject(new Error("DoDo SDK load failed"));
		document.body.appendChild(script);
	});
};

const getDodoPayments = (): DodoSdk | null => {
	const w = window as any;
	return w.DodoPayments ?? w.DodoPaymentsCheckout?.DodoPayments ?? null;
};

export const useDodoCheckout = () => {
	const { showToast } = useToast();
	const dodoInitialized = useRef(false);
	const onEventRef = useRef<(msg: string) => void>(() => {});

	const openDodoCheckout = async (
		checkoutUrl: string,
		callbacks?: { onOpened?: () => void; onClosed?: () => void; onError?: () => void }
	) => {
		try {
			await loadDodoCheckoutScript();
			const DodoPayments = getDodoPayments();
			if (!DodoPayments?.Checkout?.open) {
				window.open(checkoutUrl, "_blank", "noopener,noreferrer");
				return;
			}
			if (!dodoInitialized.current) {
				DodoPayments.Initialize({
					mode: DODO_MODE,
					displayType: "overlay",
					onEvent: (event: { event_type?: string; data?: { message?: string } }) => {
						const t = event?.event_type ?? "";
						if (t === "checkout.opened") onEventRef.current("opened");
						if (t === "checkout.error") {
							onEventRef.current("error");
							showToast(event?.data?.message ?? "Checkout error", "danger");
						}
						if (t === "checkout.closed") onEventRef.current("closed");
					},
				});
				dodoInitialized.current = true;
			}
			onEventRef.current = (msg) => {
				if (msg === "opened") callbacks?.onOpened?.();
				if (msg === "closed") callbacks?.onClosed?.();
				if (msg === "error") callbacks?.onError?.();
			};
			DodoPayments.Checkout.open({ checkoutUrl });
		} catch {
			window.open(checkoutUrl, "_blank", "noopener,noreferrer");
			callbacks?.onError?.();
		}
	};

	return { openDodoCheckout };
};
