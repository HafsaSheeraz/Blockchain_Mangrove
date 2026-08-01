import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'

vi.mock('../components/analysis/StudyAreaMap', () => ({
  default: function MockStudyAreaMap() {
    return <section aria-label="Mock study area map">Mock map</section>
  },
}))

function renderApp(initialPath = '/') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <App />
    </MemoryRouter>
  )
}

// ── Navbar ───────────────────────────────────────────────────────────────────
describe('Navbar', () => {
  it('renders the brand name', () => {
    renderApp('/')
    // Brand appears in nav; may also appear in footer — use getAllByText
    const els = screen.getAllByText(/mangrove carbon explorer/i)
    expect(els.length).toBeGreaterThan(0)
  })

  it('renders Home and Analysis nav links', () => {
    renderApp('/')
    const homeLinks     = screen.getAllByRole('link', { name: /^home$/i })
    const analysisLinks = screen.getAllByRole('link', { name: /^analysis$/i })
    expect(homeLinks.length).toBeGreaterThan(0)
    expect(analysisLinks.length).toBeGreaterThan(0)
  })

  it('renders the Launch Analyzer CTA link', () => {
    renderApp('/')
    expect(screen.getByRole('link', { name: /launch analyzer/i })).toBeInTheDocument()
  })
})

// ── Hero ─────────────────────────────────────────────────────────────────────
describe('Hero section', () => {
  it('renders the hero heading', () => {
    renderApp('/')
    expect(
      screen.getByRole('heading', { name: /explore mangrove biomass and carbon from space/i })
    ).toBeInTheDocument()
  })

  it('renders the data-source badge without Sentinel-2 as a primary input', () => {
    renderApp('/')
    // Badge should reference GEDI L2A and Global Mangrove Watch, not Sentinel-2
    expect(screen.getByText(/gedi l2a · global mangrove watch · google earth engine/i)).toBeInTheDocument()
  })

  it('renders the Start Carbon Analysis link', () => {
    renderApp('/')
    expect(screen.getByRole('link', { name: /start carbon analysis/i })).toBeInTheDocument()
  })

  it('renders the View Methodology link', () => {
    renderApp('/')
    expect(screen.getByRole('link', { name: /view methodology/i })).toBeInTheDocument()
  })

  it('shows both configured region names in the hero note', () => {
    renderApp('/')
    // "Configured study regions" appears in hero note AND in RegionSummary heading — use getAllByText
    const matches = screen.getAllByText(/configured study regions/i)
    expect(matches.length).toBeGreaterThan(0)
    // Verify the hero note specifically contains both region names
    const heroNote = matches.find(el => el.classList.contains('hero-note'))
    expect(heroNote).toBeTruthy()
    expect(heroNote.textContent).toMatch(/indus delta/i)
    expect(heroNote.textContent).toMatch(/abu dhabi/i)
  })

  it('mentions custom AOI availability', () => {
    renderApp('/')
    expect(screen.getByText(/custom aoi analysis is also available/i)).toBeInTheDocument()
  })

  it('does not display the outdated single-region note', () => {
    renderApp('/')
    expect(screen.queryByText(/currently configured for the indus delta/i)).not.toBeInTheDocument()
  })
})

// ── Metrics ──────────────────────────────────────────────────────────────────
describe('Metrics section', () => {
  it('renders the section heading labelled as Indus Delta reference results', () => {
    renderApp('/')
    expect(
      screen.getByRole('heading', { name: /indus delta reference results/i })
    ).toBeInTheDocument()
  })

  it('renders all four reference metric values', () => {
    renderApp('/')
    // 1,130 appears in both the map card stat and the metric card — use getAllByText
    expect(screen.getAllByText('1,130').length).toBeGreaterThan(0)
    expect(screen.getByText('3.09')).toBeInTheDocument()
    expect(screen.getByText('23.03')).toBeInTheDocument()
    expect(screen.getByText('90,769')).toBeInTheDocument()
  })

  it('describes the metrics as Indus-only in the section description', () => {
    renderApp('/')
    // This text appears in both the MetricCards section-desc and the footer disclaimer — use getAllByText
    const matches = screen.getAllByText(/do not apply to abu dhabi or custom aois/i)
    expect(matches.length).toBeGreaterThan(0)
  })
})

// ── How it works ──────────────────────────────────────────────────────────────
describe('How it works section', () => {
  it('renders the section heading', () => {
    renderApp('/')
    expect(
      screen.getByRole('heading', { name: /how the analysis works/i })
    ).toBeInTheDocument()
  })

  it('renders all four step titles', () => {
    renderApp('/')
    expect(screen.getByText(/select study area and dates/i)).toBeInTheDocument()
    expect(screen.getByText(/retrieve gedi l2a/i)).toBeInTheDocument()
    expect(screen.getByText(/apply biomass/i)).toBeInTheDocument()
    expect(screen.getByText(/explore maps and results/i)).toBeInTheDocument()
  })
})

// ── Scientific method ─────────────────────────────────────────────────────────
describe('Scientific method section', () => {
  it('renders the section heading', () => {
    renderApp('/')
    expect(
      screen.getByRole('heading', { name: /scientific method/i })
    ).toBeInTheDocument()
  })

  it('renders the three formula step labels', () => {
    renderApp('/')
    // Use the full "Step N — ..." text which is unique to formula cards
    expect(screen.getByText(/step 1 — above-ground biomass/i)).toBeInTheDocument()
    expect(screen.getByText(/step 2 — below-ground biomass/i)).toBeInTheDocument()
    expect(screen.getByText(/step 3 — carbon stock/i)).toBeInTheDocument()
  })

  it('renders the AGB formula variables', () => {
    renderApp('/')
    // Each formula has a .var span with text "AGB", "BGB", etc.
    const agbEls = screen.getAllByText('AGB')
    expect(agbEls.length).toBeGreaterThan(0)
  })

  it('renders the backend processing note', () => {
    renderApp('/')
    expect(screen.getByText(/google earth engine python api/i)).toBeInTheDocument()
  })
})

// ── Datasets ──────────────────────────────────────────────────────────────────
describe('Datasets section', () => {
  it('renders the section heading', () => {
    renderApp('/')
    expect(
      screen.getByRole('heading', { name: /datasets and platforms/i })
    ).toBeInTheDocument()
  })

  it('renders all four dataset names', () => {
    renderApp('/')
    // "GEDI L2A" appears in the badge AND in the datasets card — use getAllByText
    expect(screen.getAllByText(/gedi l2a/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/sentinel-2/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/global mangrove watch/i).length).toBeGreaterThan(0)
    // "Google Earth Engine" appears in badge AND dataset card — use getAllByText
    expect(screen.getAllByText(/google earth engine/i).length).toBeGreaterThan(0)
  })

  it('labels Sentinel-2 as future or experimental, not as an authoritative L2A input', () => {
    renderApp('/')
    expect(screen.getByText(/future \/ experimental/i)).toBeInTheDocument()
  })

  it('states Sentinel-2 is not used in the current authoritative calculation', () => {
    renderApp('/')
    expect(screen.getByText(/not used in the current authoritative l2a/i)).toBeInTheDocument()
  })
})

// ── Region summary ────────────────────────────────────────────────────────────
describe('Region summary section', () => {
  it('renders the configured study regions heading', () => {
    renderApp('/')
    expect(
      screen.getByRole('heading', { name: /configured study regions/i })
    ).toBeInTheDocument()
  })

  it('renders the Indus Delta region card', () => {
    renderApp('/')
    expect(screen.getByText('Indus Delta, Pakistan')).toBeInTheDocument()
  })

  it('renders the Abu Dhabi region card', () => {
    renderApp('/')
    expect(screen.getByText('Abu Dhabi, United Arab Emirates')).toBeInTheDocument()
  })

  it('renders the Custom AOI region card', () => {
    renderApp('/')
    // "Custom AOI" appears in multiple places; check the region card heading specifically
    const cards = screen.getAllByText(/custom aoi/i)
    expect(cards.length).toBeGreaterThan(0)
  })

  it('explains that predefined regions use server-side GMW assets', () => {
    renderApp('/')
    expect(screen.getByText(/predefined regions use their verified server-side gmw assets/i)).toBeInTheDocument()
  })

  it('explains that custom AOI uses the global GMW dataset', () => {
    renderApp('/')
    expect(screen.getByText(/configured global gmw dataset/i)).toBeInTheDocument()
  })

  it('warns that same polygon may differ between predefined and custom modes', () => {
    renderApp('/')
    expect(screen.getByText(/identical polygon submitted as custom aoi/i)).toBeInTheDocument()
  })
})

// ── CTA section ───────────────────────────────────────────────────────────────
describe('CTA section', () => {
  it('renders the multi-region CTA heading', () => {
    renderApp('/')
    expect(
      screen.getByRole('heading', { name: /ready to explore mangrove carbon stocks/i })
    ).toBeInTheDocument()
  })

  it('does not display the outdated single-region CTA heading', () => {
    renderApp('/')
    expect(
      screen.queryByRole('heading', { name: /ready to explore the indus delta/i })
    ).not.toBeInTheDocument()
  })

  it('renders the Open the Analysis Dashboard link', () => {
    renderApp('/')
    expect(
      screen.getByRole('link', { name: /open the analysis dashboard/i })
    ).toBeInTheDocument()
  })
})

// ── Footer ────────────────────────────────────────────────────────────────────
describe('Footer', () => {
  it('renders the research disclaimer', () => {
    renderApp('/')
    expect(screen.getByText(/research and educational purposes/i)).toBeInTheDocument()
  })
})

// ── Navigation ────────────────────────────────────────────────────────────────
describe('Navigation', () => {
  it('navigates to /analysis when Start Carbon Analysis is clicked', async () => {
    const user = userEvent.setup()
    renderApp('/')
    const link = screen.getByRole('link', { name: /start carbon analysis/i })
    await user.click(link)
    expect(screen.getByRole('heading', { name: /mangrove carbon analysis/i })).toBeInTheDocument()
  })

  it('navigates to /analysis via the CTA Open Dashboard link', async () => {
    const user = userEvent.setup()
    renderApp('/')
    const link = screen.getByRole('link', { name: /open the analysis dashboard/i })
    await user.click(link)
    expect(screen.getByRole('heading', { name: /mangrove carbon analysis/i })).toBeInTheDocument()
  })
})

// ── Analysis page (Module 2 dashboard) ──────────────────────────────────────────
describe('Analysis page', () => {
  it('renders the analysis dashboard heading', () => {
    renderApp('/analysis')
    expect(screen.getByRole('heading', { name: /mangrove carbon analysis/i })).toBeInTheDocument()
  })

  it('renders carbon-stock dashboard subtitle', () => {
    renderApp('/analysis')
    expect(
      screen.getByText(/explore live mangrove biomass and carbon estimates powered by google earth engine/i)
    ).toBeInTheDocument()
  })
})
