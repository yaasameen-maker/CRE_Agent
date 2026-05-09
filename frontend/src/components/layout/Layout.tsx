import { Outlet } from 'react-router-dom'
import TopAppBar from './TopAppBar'
import SideNav from './SideNav'

export default function Layout() {
  return (
    <div className="min-h-screen bg-background text-on-surface">
      <TopAppBar />
      <SideNav />
      <main className="md:ml-64 pt-16 px-10 py-8">
        <Outlet />
      </main>
    </div>
  )
}
