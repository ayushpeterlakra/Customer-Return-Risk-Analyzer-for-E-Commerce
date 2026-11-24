import { BarChart3, LayoutDashboard, Menu, Settings, ShieldAlert, Users, X } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { api } from '../../api/endpoints'
import { useApi } from '../../hooks/useApi'

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/customers', label: 'Customers', icon: Users },
  { to: '/monitoring', label: 'Risk monitoring', icon: ShieldAlert },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
]

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="mt-6 flex flex-col gap-1" aria-label="Main">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              isActive ? 'bg-white/10 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
            }`
          }
        >
          <Icon className="h-4 w-4" aria-hidden />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}

function Brand() {
  return (
    <div className="flex items-center gap-2.5 px-3">
      <span className="rounded-lg bg-primary p-1.5">
        <ShieldAlert className="h-4 w-4 text-white" aria-hidden />
      </span>
      <div>
        <p className="text-sm leading-tight font-semibold text-white">Return Risk</p>
        <p className="text-[11px] leading-tight text-slate-400">Analyzer</p>
      </div>
    </div>
  )
}

function ApiStatus() {
  const { data, error } = useApi(() => api.health(), [])
  const ok = data?.status === 'ok'
  const label = error ? 'API unreachable' : !data ? 'Checking API…' : ok ? `API v${data.version} online` : 'Database unavailable'
  return (
    <div className="flex items-center gap-2 px-3 text-xs text-slate-400" title={error ?? undefined}>
      <span className={`h-2 w-2 rounded-full ${error ? 'bg-red-500' : ok ? 'bg-green-500' : 'bg-amber-400'}`} aria-hidden />
      {label}
    </div>
  )
}

export function AppLayout() {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const [lastPath, setLastPath] = useState(location.pathname)
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname)
    setOpen(false)
  }

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 hidden w-60 flex-col justify-between bg-sidebar py-5 lg:flex">
        <div className="px-3">
          <Brand />
          <NavItems />
        </div>
        <div className="space-y-2">
          <ApiStatus />
          <p className="px-6 text-[11px] text-slate-500">Demo data is synthetic.</p>
        </div>
      </aside>

      <header className="sticky top-0 z-30 flex items-center justify-between bg-sidebar px-4 py-3 lg:hidden">
        <Brand />
        <button type="button" className="rounded-lg p-2 text-slate-300 hover:bg-white/10" aria-label="Open menu" onClick={() => setOpen(true)}>
          <Menu className="h-5 w-5" />
        </button>
      </header>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="absolute inset-0 bg-slate-900/50" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 flex w-64 flex-col justify-between bg-sidebar px-3 py-5">
            <div>
              <div className="flex items-center justify-between">
                <Brand />
                <button type="button" className="rounded-lg p-2 text-slate-300 hover:bg-white/10" aria-label="Close menu" onClick={() => setOpen(false)}>
                  <X className="h-5 w-5" />
                </button>
              </div>
              <NavItems onNavigate={() => setOpen(false)} />
            </div>
            <ApiStatus />
          </div>
        </div>
      )}

      <main className="px-4 py-6 sm:px-6 lg:ml-60 lg:px-10 lg:py-8">
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
