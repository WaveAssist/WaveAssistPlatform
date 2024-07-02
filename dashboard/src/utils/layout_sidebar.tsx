// src/Layout.tsx
import React, { ReactNode } from 'react';
import Sidebar from './sidebar';
import { Container } from 'react-bootstrap';

interface LayoutProps {
  children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="d-flex">
      <Sidebar />
      <Container fluid>
        {children}
      </Container>
    </div>
  );
};

export default Layout;
