import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { AuthProvider, useAuth } from './context/AuthContext';

// Pages
import { LoginPage } from './pages/LoginPage';
import { Overview } from './pages/Overview';
import { RiskNetwork } from './pages/RiskNetwork';
import { Decisions } from './pages/Decisions';
import { Transfers } from './pages/Transfers';
import { TransferDetails } from './pages/TransferDetails';
import { Outcomes } from './pages/Outcomes';
import { History } from './pages/History';
import { Agent } from './pages/Agent';
import { Simulation } from './pages/Simulation';
import { SimulationSetup } from './pages/SimulationSetup';
import { RecoveryOrdersPage } from './pages/RecoveryOrdersPage';

const RequireAuth = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 text-slate-500">
        <div className="w-8 h-8 rounded-full border-2 border-emerald-500 border-t-transparent animate-spin mb-3" />
        <span className="text-xs font-bold uppercase tracking-widest">Verifying Session...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    const requestedPath = `${location.pathname}${location.search}`;
    return <Navigate to="/login" state={{ from: requestedPath }} replace />;
  }

  return <>{children}</>;
};

const SimulationGuard = ({ children }: { children: React.ReactNode }) => {
  const isInitialized = sessionStorage.getItem('restock_simulation_initialized');
  if (!isInitialized) {
    return <Navigate to="/setup" replace />;
  }
  return <>{children}</>;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/setup"
            element={
              <RequireAuth>
                <SimulationSetup />
              </RequireAuth>
            }
          />

          <Route
            path="/"
            element={
              <RequireAuth>
                <SimulationGuard>
                  <Layout />
                </SimulationGuard>
              </RequireAuth>
            }
          >
            <Route index element={<Overview />} />
            <Route path="risk" element={<RiskNetwork />} />
            <Route path="decisions" element={<Decisions />} />
            <Route path="transfers" element={<Transfers />} />
            <Route path="transfers/:transferId" element={<TransferDetails />} />
            <Route path="outcomes" element={<Outcomes />} />
            <Route path="history" element={<History />} />
            <Route path="agent" element={<Agent />} />
            <Route path="simulation" element={<Simulation />} />
            <Route path="workflow" element={<Simulation />} />
            <Route path="payments" element={<RecoveryOrdersPage />} />
            <Route path="checkout" element={<RecoveryOrdersPage />} />
            <Route path="checkout/success" element={<RecoveryOrdersPage />} />
            <Route path="checkout/cancel" element={<RecoveryOrdersPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
