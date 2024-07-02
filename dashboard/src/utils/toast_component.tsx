import React from 'react';
import { Toast, ToastContainer } from 'react-bootstrap';

interface AutoDismissToastProps {
    show: boolean;
    setShow: (show: boolean) => void;
    message: string;
    variant: string;
}

const AutoDismissToast: React.FC<AutoDismissToastProps> = ({ show, setShow, message, variant }) => {
    return (
        <ToastContainer position="top-end" className="p-3">
            <Toast onClose={() => setShow(false)} show={show} delay={3000} autohide className={`text-bg-${variant} border-0`} role="alert" aria-live="assertive" aria-atomic="true">
                <div className="d-flex">
                    <div className="toast-body">
                        {message}
                    </div>
                    <button type="button" className="btn-close btn-close-white me-2 m-auto" 
                            onClick={() => setShow(false)}  // Add onClick event handler here
                            aria-label="Close"></button>
                </div>
            </Toast>
        </ToastContainer>
    );
};

export default AutoDismissToast;
