import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';

// Pages
import { Overview } from './pages/Overview';
import { RiskNetwork } from './pages/RiskNetwork';
import { Decisions } from './pages/Decisions';
import { Transfers } from './pages/Transfers';
import { TransferDetails } from './pages/TransferDetails';
import { Outcomes } from './pages/Outcomes';
import { History } from './pages/History';
import { Agent } from './pages/Agent';
import { Workflow } from './pages/Workflow';
import { SimulationSetup } from './pages/SimulationSetup';

const SimulationGuard = ({ children }: { children: React.ReactNode }) => {
  const isInitialized = sessionStorage.getItem('restock_simulation_initialized');
  if (!isInitialized) {
    return <Navigate to="/setup" replace />;
  }
  return <>{children}</>;
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/setup" element={<SimulationSetup />} />
        
        <Route path="/" element={
          <SimulationGuard>
            <Layout />
          </SimulationGuard>
        }>
          <Route index element={<Overview />} />
          <Route path="risk" element={<RiskNetwork />} />
          <Route path="decisions" element={<Decisions />} />
          <Route path="transfers" element={<Transfers />} />
          <Route path="transfers/:transferId" element={<TransferDetails />} />
          <Route path="outcomes" element={<Outcomes />} />
          <Route path="history" element={<History />} />
          <Route path="agent" element={<Agent />} />
          <Route path="workflow" element={<Workflow />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
