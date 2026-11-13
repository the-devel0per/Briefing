import { Bitcoin, Cpu, Landmark, TrendingUp, type LucideIcon } from 'lucide-react'
import type { CategoryId, HumourMode } from '../types'

export const CATEGORIES: { id: CategoryId; label: string; Icon: LucideIcon }[] = [
  { id: 'technology', label: 'Technology', Icon: Cpu },
  { id: 'government', label: 'Government & Policy', Icon: Landmark },
  { id: 'crypto', label: 'Crypto', Icon: Bitcoin },
  { id: 'stocks', label: 'Stocks & Markets', Icon: TrendingUp },
]
export const categoryMeta = (id: CategoryId) => CATEGORIES.find((c) => c.id === id) ?? CATEGORIES[0]

export const TONES: { id: HumourMode; label: string }[] = [
  { id: 'sarcastic', label: 'Sarcastic' },
  { id: 'genz', label: 'Gen Z' },
  { id: 'unhinged', label: 'Unhinged' },
]
