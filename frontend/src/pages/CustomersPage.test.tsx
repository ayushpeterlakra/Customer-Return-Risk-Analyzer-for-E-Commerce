import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api/endpoints'
import { CustomersPage } from './CustomersPage'

afterEach(() => vi.restoreAllMocks())

const page = {
  items: [
    { customer_id: 'CUST0001', name: 'Test Person', total_orders: 10, total_returns: 6, return_percentage: 60, risk_score: 85, risk_level: 'HIGH' as const, last_return_date: '2026-11-01', review_status: 'PENDING_REVIEW' as const },
  ],
  total: 1,
  page: 1,
  page_size: 20,
  pages: 1,
}

describe('CustomersPage', () => {
  it('renders rows from the API and passes URL filters through', async () => {
    const spy = vi.spyOn(api, 'customers').mockResolvedValue(page)
    render(
      <MemoryRouter initialEntries={['/customers?risk_level=HIGH&high_ratio=1']}>
        <CustomersPage />
      </MemoryRouter>,
    )
    expect(await screen.findByText('Test Person')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View profile' })).toHaveAttribute('href', '/customers/CUST0001')
    await waitFor(() => expect(spy).toHaveBeenCalledWith(expect.objectContaining({ risk_level: 'HIGH', min_return_ratio: 0.3, page: 1 })))
  })

  it('shows an error state when the API fails', async () => {
    vi.spyOn(api, 'customers').mockRejectedValue(new Error('Network down'))
    render(
      <MemoryRouter>
        <CustomersPage />
      </MemoryRouter>,
    )
    expect(await screen.findByRole('alert')).toHaveTextContent('Network down')
  })
})
