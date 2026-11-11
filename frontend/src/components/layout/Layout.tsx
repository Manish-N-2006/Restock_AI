import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { AlertBanner } from './AlertBanner';

export const Layout: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);

  // Play startup splash animation on initial app launch
  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 1200);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="min-h-screen bg-white text-slate-900 font-sans antialiased selection:bg-emerald-100 selection:text-emerald-900">
      <AnimatePresence mode="wait">
        {loading ? (
          /* 1. Opening Splash Animation Screen */
          <motion.div
            key="splash"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.4, ease: 'easeInOut' }}
            className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white"
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: [0.8, 1.05, 1], opacity: 1 }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
              className="flex items-center gap-3"
            >
              <div className="w-12 h-12 rounded-2xl bg-emerald-500 flex items-center justify-center shadow-lg shadow-emerald-200">
                <span className="text-white text-2xl font-black">⚡</span>
              </div>
              <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
                ReStock<span className="text-emerald-600">AI</span>
              </h1>
            </motion.div>

            {/* Glowing progress line */}
            <div className="w-48 h-1.5 bg-slate-100 rounded-full mt-6 overflow-hidden">
              <motion.div
                initial={{ x: '-100%' }}
                animate={{ x: '100%' }}
                transition={{ repeat: Infinity, duration: 1, ease: 'easeInOut' }}
                className="w-full h-full bg-emerald-500"
              />
            </div>
            <p className="mt-3 text-[11px] font-bold text-slate-400 uppercase tracking-widest">
              Initializing Engine Network
            </p>
          </motion.div>
        ) : (
          /* 2. Main Dashboard Application Layout */
          <motion.div
            key="dashboard"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
            className="flex h-screen overflow-hidden bg-slate-50/50"
          >
            <Sidebar />
            <div className="flex flex-col flex-1 overflow-hidden border-l border-slate-200/80 bg-white">
              <Topbar />
              <AlertBanner />
              <main className="flex-1 overflow-y-auto p-6 lg:p-8 bg-slate-50/30">
                <div className="max-w-7xl mx-auto">
                  <Outlet />
                </div>
              </main>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};