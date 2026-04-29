import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import DigestList from './pages/DigestList'
import OpportunityDetail from './pages/OpportunityDetail'
import ActionAlerts from './pages/ActionAlerts'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DigestList />} />
          <Route path="brief/:zip" element={<OpportunityDetail />} />
          <Route path="alerts" element={<ActionAlerts />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
