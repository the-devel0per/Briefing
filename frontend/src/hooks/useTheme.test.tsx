import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { useTheme } from './useTheme'

describe('useTheme', () => {
  beforeEach(() => { localStorage.clear(); document.documentElement.className = '' })

  it('mirrors the class applied before paint', () => {
    document.documentElement.classList.add('dark')
    expect(renderHook(() => useTheme()).result.current.theme).toBe('dark')
  })

  it('toggles the html class and persists the choice', () => {
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('light')
    act(() => result.current.toggle())
    expect(result.current.theme).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('theme')).toBe('dark')
    act(() => result.current.toggle())
    expect(localStorage.getItem('theme')).toBe('light')
  })
})
