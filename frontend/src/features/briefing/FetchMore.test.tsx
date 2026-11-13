import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { FetchMore } from './FetchMore'

const base = { used: 0, max: 2, remaining: 2, exhausted: false, canFetchMore: true }

describe('FetchMore', () => {
  it('requests more and shows remaining batches', async () => {
    const onFetch = vi.fn()
    render(<FetchMore state={base} loading={false} message={null} onFetch={onFetch} />)
    expect(screen.getByText(/2 of 2 extra batches left/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Fetch More' }))
    expect(onFetch).toHaveBeenCalledTimes(1)
  })

  it('disables the button while loading', () => {
    render(<FetchMore state={base} loading message={null} onFetch={() => {}} />)
    expect(screen.getByRole('button', { name: /fetching/i })).toBeDisabled()
  })

  it('shows the caught-up message and no button once the quota is exhausted', () => {
    render(<FetchMore state={{ ...base, used: 2, remaining: 0, exhausted: true }} loading={false} message={null} onFetch={() => {}} />)
    expect(screen.getByText("You've caught up with today's briefing.")).toBeInTheDocument()
    expect(screen.getByText(/next daily update/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /fetch more/i })).not.toBeInTheDocument()
  })

  it('announces errors in a live region', () => {
    render(<FetchMore state={base} loading={false} message="Network error." onFetch={() => {}} />)
    expect(screen.getByRole('status')).toHaveTextContent('Network error.')
  })
})
