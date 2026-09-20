import { BrowserRouter, Routes, Route } from 'react-router-dom';
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

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
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
