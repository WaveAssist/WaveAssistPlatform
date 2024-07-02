// ToastContext.tsx
import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { Toast, ToastContextType } from './types';
import AutoDismissToast from './toast_component';

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [toast, setToast] = useState<Toast>({ show: false, message: '', variant: 'primary' });

    const showToast = useCallback((message: string, variant: string = 'primary') => {
        setToast({ show: true, message, variant });
    }, []);

    const hideToast = useCallback(() => {
        setToast((prevToast) => ({ ...prevToast, show: false }));
    }, []);

    return (
        <ToastContext.Provider value={{ toast, showToast, hideToast }}>
            {children}
            <AutoDismissToast
                show={toast.show}
                setShow={(show) => setToast((prevToast) => ({ ...prevToast, show }))}
                message={toast.message}
                variant={toast.variant}
            />
        </ToastContext.Provider>
    );
};

export const useToast = (): ToastContextType => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
};
