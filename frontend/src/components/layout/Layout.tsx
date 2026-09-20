import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { AlertBanner } from './AlertBanner';

export const Layout: React.FC = () => {
  return (
    <div className="flex h-screen overflow-hidden bg-page text-text-primary">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar />
        <AlertBanner />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
