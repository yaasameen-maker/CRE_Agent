import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import AnalyticsDashboard from './pages/AnalyticsDashboard'
import Research from './pages/Research'
import Pipeline from './pages/Pipeline'
import OpportunityDetail from './pages/OpportunityDetail'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<AnalyticsDashboard />} />
          <Route path="research" element={<Research />} />
          <Route path="pipeline" element={<Pipeline />} />
          <Route path="brief/:zip" element={<OpportunityDetail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
