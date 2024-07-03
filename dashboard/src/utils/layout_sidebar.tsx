// src/Layout.tsx
import React, { ReactNode } from 'react';
import Sidebar from './sidebar';
import NavbarComponent from './navbar';
import { Container } from 'react-bootstrap';

interface LayoutProps {
  children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="d-flex vh-100">
      <Sidebar />
      <div className="d-flex flex-column flex-grow-1">
        <NavbarComponent />
        <Container fluid className="flex-grow-1 p-3">
          {children}
        </Container>
      </div>
    </div>
  );
};

export default Layout;
