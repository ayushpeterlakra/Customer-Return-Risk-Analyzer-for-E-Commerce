import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ChartFrame } from '../charts/ChartFrame'
import { ReviewBadge, RiskBadge } from './Badge'
import { Pagination } from './Pagination'

describe('badges', () => {
  it('labels risk levels and unscored customers', () => {
    render(
      <>
        <RiskBadge level="HIGH" />
        <RiskBadge level={null} />
        <ReviewBadge status="UNDER_INVESTIGATION" />
      </>,
    )
    expect(screen.getByText('High')).toBeInTheDocument()
    expect(screen.getByText('Not scored')).toBeInTheDocument()
    expect(screen.getByText('Under investigation')).toBeInTheDocument()
  })
})

describe('Pagination', () => {
  it('shows the range and disables buttons at the edges', () => {
    const onChange = vi.fn()
    render(<Pagination page={1} pages={3} total={45} pageSize={20} onChange={onChange} />)
    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
    expect(screen.getByLabelText('Previous page')).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Next page'))
    expect(onChange).toHaveBeenCalledWith(2)
  })
})

describe('ChartFrame', () => {
  const base = { title: 'Chart', onRetry: vi.fn(), children: <p>chart body</p> }
  it('shows an error with a retry button', () => {
    render(<ChartFrame {...base} loading={false} error="Boom" empty={false} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Boom')
    fireEvent.click(screen.getByText('Try again'))
    expect(base.onRetry).toHaveBeenCalled()
  })
  it('shows an empty state', () => {
    render(<ChartFrame {...base} loading={false} error={null} empty />)
    expect(screen.getByText('No data for this selection')).toBeInTheDocument()
  })
  it('renders the chart when data is present', () => {
    render(<ChartFrame {...base} loading={false} error={null} empty={false} />)
    expect(screen.getByText('chart body')).toBeInTheDocument()
  })
})
