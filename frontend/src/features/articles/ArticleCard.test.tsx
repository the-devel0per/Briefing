import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { article } from '../../test/fixtures'
import { ArticleCard } from './ArticleCard'

describe('ArticleCard', () => {
  it('shows AI and original headlines with both labels and a safe external link', () => {
    render(<ArticleCard article={article()} />)
    expect(screen.getByText('Nvidia unveils chip, humanity braces')).toBeInTheDocument()
    expect(screen.getByText('Nvidia unveils new AI chip')).toBeInTheDocument()
    expect(screen.getByText('AI rewrite')).toBeInTheDocument()
    expect(screen.getByText('Original')).toBeInTheDocument()
    const link = screen.getByRole('link', { name: /read original/i })
    expect(link).toHaveAttribute('href', 'https://example.com/story')
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'))
    expect(screen.getByText(/\+2 sources/)).toBeInTheDocument()
  })

  it('falls back to original headline only when there is no AI rewrite', () => {
    render(<ArticleCard article={article({ aiHeadline: null, aiMode: null })} />)
    expect(screen.queryByText('AI rewrite')).not.toBeInTheDocument()
    expect(screen.getByText('Original')).toBeInTheDocument()
  })

  it('reserves image space, lazy-loads and swaps to a neutral fallback when the image breaks', () => {
    render(<ArticleCard article={article()} index={5} />)
    const img = screen.getByAltText('Chip photo')
    expect(img).toHaveAttribute('loading', 'lazy')
    expect(img).toHaveAttribute('width'); expect(img).toHaveAttribute('height')
    fireEvent.error(img)
    expect(screen.queryByAltText('Chip photo')).not.toBeInTheDocument()
    expect(screen.getByTestId('image-fallback')).toBeInTheDocument()
  })

  it('renders without an image', () => {
    render(<ArticleCard article={article({ image: null })} />)
    expect(screen.getByTestId('image-fallback')).toBeInTheDocument()
  })
})
