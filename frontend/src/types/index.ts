export type CategoryId = 'technology' | 'government' | 'crypto' | 'stocks'
export type HumourMode = 'witty' | 'roast' | 'sarcastic' | 'deadpan' | 'genz' | 'unhinged'

export interface ArticleImage { url: string; source: string; attribution: string | null; alt: string; status: string | null }

export interface Article {
  id: string
  category: CategoryId
  originalTitle: string
  aiHeadline: string | null
  aiMode: HumourMode | null
  publisher: string
  publishedAt: string
  summary: string | null
  url: string
  coverage: number
  alsoReportedBy: string[]
  image: ArticleImage | null
}

export interface Preferences { mutedCategories: CategoryId[]; humourMode: HumourMode }
export interface FetchMoreState { used: number; max: number; remaining: number; exhausted: boolean; canFetchMore?: boolean }

export interface Briefing {
  date: string
  lastUpdated: string | null
  target: number
  articles: Article[]
  total: number
  activeCategories: CategoryId[]
  categoryCounts: Record<CategoryId, number>
  notice: string | null
  preferences: Preferences
  fetchMore: FetchMoreState & { canFetchMore: boolean }
}

export interface FetchMoreResponse { articles: Article[]; replayed: boolean; fetchMore: FetchMoreState }
