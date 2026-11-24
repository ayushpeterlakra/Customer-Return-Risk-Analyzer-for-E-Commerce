import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="py-24 text-center">
      <p className="text-sm font-semibold text-primary">404</p>
      <h1 className="mt-2 text-2xl font-semibold">Page not found</h1>
      <Link to="/" className="mt-4 inline-block text-sm text-primary hover:underline">
        Back to overview
      </Link>
    </div>
  )
}
