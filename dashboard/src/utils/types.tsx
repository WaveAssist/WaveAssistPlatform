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
