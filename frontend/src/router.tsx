import { createBrowserRouter } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { Skeleton } from './components/ui/States'

// Pages load on demand so the first screen downloads less JavaScript.
export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    HydrateFallback: () => <Skeleton className="h-96" />,
    children: [
      { path: '/', lazy: () => import('./pages/OverviewPage').then((m) => ({ Component: m.OverviewPage })) },
      { path: '/customers', lazy: () => import('./pages/CustomersPage').then((m) => ({ Component: m.CustomersPage })) },
      { path: '/customers/:customerId', lazy: () => import('./pages/CustomerDetailPage').then((m) => ({ Component: m.CustomerDetailPage })) },
      { path: '/monitoring', lazy: () => import('./pages/MonitoringPage').then((m) => ({ Component: m.MonitoringPage })) },
      { path: '/analytics', lazy: () => import('./pages/AnalyticsPage').then((m) => ({ Component: m.AnalyticsPage })) },
      { path: '/settings', lazy: () => import('./pages/SettingsPage').then((m) => ({ Component: m.SettingsPage })) },
      { path: '*', lazy: () => import('./pages/NotFoundPage').then((m) => ({ Component: m.NotFoundPage })) },
    ],
  },
])
