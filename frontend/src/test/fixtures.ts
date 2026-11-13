import type { Article } from '../types'

export const article = (over: Partial<Article> = {}): Article => ({
  id: 'a'.repeat(16), category: 'technology', originalTitle: 'Nvidia unveils new AI chip', aiHeadline: 'Nvidia unveils chip, humanity braces',
  aiMode: 'witty', publisher: 'Reuters', publishedAt: new Date(Date.now() - 3_600_000).toISOString(), summary: 'A summary.',
  url: 'https://example.com/story', coverage: 3, alsoReportedBy: ['BBC News', 'CNBC'],
  image: { url: 'https://img.example.com/a.jpg', source: 'rss', attribution: 'Image: Reuters', alt: 'Chip photo', status: 'unverified' }, ...over,
})
