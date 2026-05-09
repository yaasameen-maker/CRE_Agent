import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import AnalyticsDashboard from './pages/AnalyticsDashboard'
import Research from './pages/Research'
import Pipeline from './pages/Pipeline'
import AiAssistant from './pages/AiAssistant'
import OpportunityDetail from './pages/OpportunityDetail'
import DataSources from './pages/DataSources'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Pipeline />} />
          <Route path="analytics" element={<AnalyticsDashboard />} />
          <Route path="research" element={<Research />} />
          <Route path="data-sources" element={<DataSources />} />
          <Route path="assistant" element={<AiAssistant />} />
          <Route path="brief/:zip" element={<OpportunityDetail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
