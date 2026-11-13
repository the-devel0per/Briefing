import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Preferences } from '../../types'
import { CategoryPanel } from './CategoryPanel'

const counts = { technology: 12, government: 8, crypto: 9, stocks: 7 }
const setup = (prefs: Preferences) => {
  const onChange = vi.fn()
  render(<CategoryPanel preferences={prefs} counts={counts} onChange={onChange} onSynced={() => {}} />)
  return onChange
}

describe('CategoryPanel', () => {
  it('mutes a category', async () => {
    const onChange = setup({ mutedCategories: [], humourMode: 'witty' })
    await userEvent.click(screen.getByRole('switch', { name: /Government & Policy/ }))
    expect(onChange).toHaveBeenCalledWith({ mutedCategories: ['government'], humourMode: 'witty' })
  })

  it('unmutes a category and reflects state via aria-checked', async () => {
    const onChange = setup({ mutedCategories: ['crypto'], humourMode: 'witty' })
    const crypto = screen.getByRole('switch', { name: /Crypto/ })
    expect(crypto).toHaveAttribute('aria-checked', 'false')
    await userEvent.click(crypto)
    expect(onChange).toHaveBeenCalledWith({ mutedCategories: [], humourMode: 'witty' })
  })

  it('never allows muting the last active category', async () => {
    const onChange = setup({ mutedCategories: ['government', 'crypto', 'stocks'], humourMode: 'witty' })
    const tech = screen.getByRole('switch', { name: /Technology/ })
    expect(tech).toBeDisabled()
    await userEvent.click(tech)
    expect(onChange).not.toHaveBeenCalled()
  })

  it('changes tone', async () => {
    const onChange = setup({ mutedCategories: [], humourMode: 'witty' })
    await userEvent.selectOptions(screen.getByLabelText(/headline tone/i), 'sarcastic')
    expect(onChange).toHaveBeenCalledWith({ mutedCategories: [], humourMode: 'sarcastic' })
  })
})
