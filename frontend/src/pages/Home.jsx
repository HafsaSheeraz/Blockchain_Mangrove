import { Link } from 'react-router-dom'
import './Home.css'

/* ─── SVG icon primitives ──────────────────────────────────────────────── */
const MangroveIcon = () => (
  <svg viewBox="0 0 32 32" fill="currentColor" aria-hidden="true">
    <ellipse cx="16" cy="11" rx="9" ry="7" />
    <ellipse cx="9"  cy="17" rx="6" ry="5" />
    <ellipse cx="23" cy="17" rx="6" ry="5" />
    <rect x="15" y="19" width="2" height="9" rx="1" />
    <line x1="15" y1="24" x2="10" y2="29" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    <line x1="17" y1="24" x2="22" y2="29" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
)

const ArrowIcon = () => (
  <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16" aria-hidden="true">
    <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
  </svg>
)

const PinIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" />
    <circle cx="12" cy="9" r="2.5" />
  </svg>
)

const SatelliteIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="12" cy="12" r="3" />
    <path d="M6.3 6.3l11.4 11.4M6.3 17.7L17.7 6.3" />
    <path d="M3 12h2m14 0h2M12 3v2m0 14v2" />
  </svg>
)

const FormulaIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M4 7l2-3h12l2 3" />
    <path d="M6 4l6 16 6-16" />
    <path d="M10 13h4" />
  </svg>
)

const ChartIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <rect x="3"  y="12" width="4" height="9" />
    <rect x="10" y="7"  width="4" height="14" />
    <rect x="17" y="3"  width="4" height="18" />
    <line x1="2" y1="21" x2="22" y2="21" />
  </svg>
)

const PulseIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="14" height="14" aria-hidden="true">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </svg>
)

/* ─── Abstract Indus Delta map SVG ─────────────────────────────────────── */
const DeltaMapSVG = () => (
  <svg
    viewBox="0 0 480 295"
    xmlns="http://www.w3.org/2000/svg"
    role="img"
    aria-label="Abstract preview map of the Indus Delta mangrove region"
  >
    <defs>
      <linearGradient id="lgCarbon" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%"   stopColor="#f59e0b" />
        <stop offset="45%"  stopColor="#34d399" />
        <stop offset="100%" stopColor="#0d9488" />
      </linearGradient>
      <linearGradient id="lgSea" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%"   stopColor="#071a2e" />
        <stop offset="100%" stopColor="#05121f" />
      </linearGradient>
    </defs>

    {/* Ocean background */}
    <rect width="480" height="295" fill="url(#lgSea)" />

    {/* Lat / lon grid */}
    <g stroke="#0f2d45" strokeWidth="0.6" opacity="0.9">
      <line x1="0" y1="60"  x2="480" y2="60"  />
      <line x1="0" y1="120" x2="480" y2="120" />
      <line x1="0" y1="180" x2="480" y2="180" />
      <line x1="0" y1="240" x2="480" y2="240" />
      <line x1="80"  y1="0" x2="80"  y2="295" />
      <line x1="160" y1="0" x2="160" y2="295" />
      <line x1="240" y1="0" x2="240" y2="295" />
      <line x1="320" y1="0" x2="320" y2="295" />
      <line x1="400" y1="0" x2="400" y2="295" />
    </g>

    {/* Coordinate labels */}
    <g fill="#1e4a63" fontSize="7" fontFamily="ui-monospace,Consolas,monospace">
      <text x="4" y="58">25.0°N</text>
      <text x="4" y="118">24.5°N</text>
      <text x="4" y="178">24.0°N</text>
      <text x="4" y="238">23.5°N</text>
      <text x="75"  y="289" textAnchor="middle">67.0°E</text>
      <text x="155" y="289" textAnchor="middle">67.5°E</text>
      <text x="235" y="289" textAnchor="middle">68.0°E</text>
      <text x="315" y="289" textAnchor="middle">68.5°E</text>
    </g>

    {/* Delta land mass — fan shape from apex to coast */}
    <path
      d="M 240,18
         C 215,55 190,90 168,130
         C 148,165 125,200 105,242
         L 130,256
         C 160,246 192,240 220,238
         C 232,237 236,237 240,237
         C 244,237 248,237 260,238
         C 288,240 320,246 352,256
         L 376,242
         C 358,200 336,165 316,130
         C 292,90 266,55 240,18 Z"
      fill="#8a7258"
      opacity="0.92"
    />

    {/* Main water channels (dark cuts through delta) */}
    <path d="M 240,18 C 228,72 215,128 208,182 C 203,212 200,234 198,260"
          stroke="#071a2e" strokeWidth="11" fill="none" strokeLinecap="round" />
    <path d="M 240,18 C 244,88 246,150 248,200 C 249,222 249,242 249,262"
          stroke="#071a2e" strokeWidth="7"  fill="none" strokeLinecap="round" />
    <path d="M 200,75 C 190,115 182,158 177,200 C 174,220 172,244 170,262"
          stroke="#071a2e" strokeWidth="8"  fill="none" strokeLinecap="round" />
    <path d="M 280,75 C 292,115 300,158 305,200 C 308,222 310,244 312,262"
          stroke="#071a2e" strokeWidth="8"  fill="none" strokeLinecap="round" />

    {/* Small estuary pools */}
    <ellipse cx="210" cy="248" rx="12" ry="7"  fill="#071a2e" opacity="0.9" />
    <ellipse cx="254" cy="252" rx="9"  ry="5"  fill="#071a2e" opacity="0.9" />

    {/* Mangrove patches — left group */}
    <ellipse cx="125" cy="215" rx="24" ry="14" fill="#2d6a4f" opacity="0.9" />
    <ellipse cx="140" cy="232" rx="20" ry="11" fill="#40916c" opacity="0.88" />
    <ellipse cx="154" cy="246" rx="15" ry="8"  fill="#2d6a4f" opacity="0.88" />
    <ellipse cx="133" cy="246" rx="11" ry="6"  fill="#52b788" opacity="0.85" />

    {/* Mangrove patches — centre */}
    <path d="M 218,234 Q 228,224 240,228 Q 252,224 262,234 Q 257,250 240,248 Q 223,250 218,234 Z"
          fill="#2d6a4f" opacity="0.9" />
    <ellipse cx="240" cy="247" rx="15" ry="7" fill="#40916c" opacity="0.88" />

    {/* Mangrove patches — right group */}
    <ellipse cx="345" cy="212" rx="22" ry="13" fill="#2d6a4f" opacity="0.9" />
    <ellipse cx="358" cy="230" rx="18" ry="10" fill="#40916c" opacity="0.88" />
    <ellipse cx="347" cy="244" rx="14" ry="7"  fill="#2d6a4f" opacity="0.88" />
    <ellipse cx="368" cy="244" rx="11" ry="6"  fill="#52b788" opacity="0.85" />

    {/* Coastline (dashed) */}
    <path
      d="M 105,254 C 145,247 185,242 215,240 C 228,239 234,238 240,238 C 246,238 253,239 266,240 C 296,242 335,247 375,254"
      stroke="#2a6a8a" strokeWidth="1.2" fill="none" strokeDasharray="5,3"
    />

    {/* GEDI sample points (amber = low carbon → teal = high carbon) */}
    {[
      { cx: 128, cy: 212, fill: '#f59e0b' },
      { cx: 142, cy: 225, fill: '#fbbf24' },
      { cx: 133, cy: 238, fill: '#34d399' },
      { cx: 148, cy: 242, fill: '#0d9488' },
      { cx: 156, cy: 248, fill: '#0d9488' },
      { cx: 222, cy: 236, fill: '#34d399' },
      { cx: 240, cy: 232, fill: '#0d9488' },
      { cx: 256, cy: 238, fill: '#2dd4bf' },
      { cx: 230, cy: 246, fill: '#34d399' },
      { cx: 248, cy: 248, fill: '#0d9488' },
      { cx: 346, cy: 210, fill: '#fbbf24' },
      { cx: 358, cy: 224, fill: '#34d399' },
      { cx: 350, cy: 236, fill: '#0d9488' },
      { cx: 364, cy: 240, fill: '#34d399' },
      { cx: 338, cy: 244, fill: '#f59e0b' },
      { cx: 372, cy: 246, fill: '#2dd4bf' },
    ].map((pt, i) => (
      <circle key={i} cx={pt.cx} cy={pt.cy} r="3.2"
              fill={pt.fill} stroke="#fff" strokeWidth="0.9" opacity="0.95" />
    ))}

    {/* North arrow */}
    <g transform="translate(455,22)">
      <polygon points="0,-11 -4,3 0,0 4,3" fill="#4a7a96" />
      <text y="17" fill="#4a7a96" fontSize="9" textAnchor="middle"
            fontFamily="system-ui,sans-serif" fontWeight="700">N</text>
    </g>

    {/* Scale bar */}
    <g transform="translate(380,275)">
      <line x1="0" y1="0" x2="72" y2="0" stroke="#2a5a74" strokeWidth="1.5" />
      <line x1="0"  y1="-4" x2="0"  y2="4" stroke="#2a5a74" strokeWidth="1.5" />
      <line x1="72" y1="-4" x2="72" y2="4" stroke="#2a5a74" strokeWidth="1.5" />
      <text x="36" y="13" fill="#2a5a74" fontSize="7"
            fontFamily="ui-monospace,Consolas,monospace" textAnchor="middle">50 km</text>
    </g>

    {/* Top-left location label */}
    <rect x="7" y="7" width="148" height="16" rx="4" fill="rgba(5,18,31,0.88)" />
    <text x="13" y="19" fill="#4a7a96" fontSize="7.5"
          fontFamily="ui-monospace,Consolas,monospace" letterSpacing="0.3">
      Indus Delta  ·  23°N 68°E
    </text>

    {/* Preview badge */}
    <rect x="338" y="7" width="134" height="16" rx="8"
          fill="rgba(251,191,36,0.1)" stroke="rgba(251,191,36,0.3)" strokeWidth="0.6" />
    <text x="405" y="19" fill="#fbbf24" fontSize="7.5" textAnchor="middle"
          fontFamily="system-ui,sans-serif" fontWeight="700" letterSpacing="0.5">
      PREVIEW — NOT LIVE
    </text>
  </svg>
)

/* ─── Sections ──────────────────────────────────────────────────────────── */
function Navbar() {
  return (
    <nav className="nav" aria-label="Main navigation">
      <div className="nav-inner">
        <Link to="/" className="nav-logo" aria-label="Mangrove Carbon Explorer home">
          <span className="nav-logo-icon">
            <MangroveIcon />
          </span>
          <span className="nav-brand">Mangrove Carbon Explorer</span>
        </Link>

        <div className="nav-links">
          <Link to="/"         className="nav-link">Home</Link>
          <Link to="/analysis" className="nav-link">Analysis</Link>
          <Link to="/analysis" className="nav-cta">Launch Analyzer</Link>
        </div>
      </div>
    </nav>
  )
}

function Hero() {
  return (
    <section className="hero" aria-labelledby="hero-heading">
      <div className="hero-inner">

        {/* Left column */}
        <div className="hero-left">
          <div className="hero-badge anim-1">
            <span className="hero-badge-dot" aria-hidden="true" />
            GEDI L2A · Global Mangrove Watch · Google Earth Engine
          </div>

          <h1 id="hero-heading" className="hero-title anim-2">
            Explore mangrove <em>biomass and carbon</em> from space
          </h1>

          <p className="hero-desc anim-3">
            Use NASA GEDI L2A canopy height and Global Mangrove Watch coverage to estimate
            height-based mangrove biomass and carbon through Google Earth Engine.
          </p>

          <div className="hero-actions anim-4">
            <Link to="/analysis" className="btn-primary">
              Start Carbon Analysis <ArrowIcon />
            </Link>
            <a href="#methodology" className="btn-secondary">
              View Methodology
            </a>
          </div>

          <p className="hero-note anim-5">
            <PulseIcon />
            Configured study regions: Indus Delta, Pakistan and Abu Dhabi, United Arab Emirates.
            Custom AOI analysis is also available.
          </p>
        </div>

        {/* Right column — map card */}
        <div className="hero-right anim-3">
          <div className="map-card" role="figure" aria-label="Indus Delta sample data preview">
            <div className="map-card-header">
              <span className="map-card-dot" style={{ background: '#ef4444' }} aria-hidden="true" />
              <span className="map-card-dot" style={{ background: '#f59e0b' }} aria-hidden="true" />
              <span className="map-card-dot" style={{ background: '#22c55e' }} aria-hidden="true" />
              <span className="map-card-title">Indus Delta — Mangrove Carbon Preview</span>
              <span className="map-card-coords">23°35′N · 67°44′E</span>
              <span className="map-tag">Sample Data</span>
            </div>

            <div className="map-card-body">
              <DeltaMapSVG />
            </div>

            <div className="map-card-footer">
              <div className="map-legend">
                <span className="map-legend-label">Carbon density (Mg C/ha)</span>
                <div className="legend-bar" role="presentation" />
                <div className="legend-ticks" aria-hidden="true">
                  <span className="legend-tick">Low</span>
                  <span className="legend-tick">~23</span>
                  <span className="legend-tick">High</span>
                </div>
              </div>
              <div className="map-stat">
                <span className="map-stat-value">1,130</span>
                <span className="map-stat-label">GEDI shots</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function MetricCards() {
  const metrics = [
    { value: '1,130', unit: '',        desc: 'Valid GEDI L2A samples in the study region' },
    { value: '3.09',  unit: 'm',       desc: 'Mean canopy height (RH98) across samples' },
    { value: '23.03', unit: 'Mg C/ha', desc: 'Mean carbon density across mangrove patches' },
    { value: '90,769', unit: 'ha',     desc: 'Mapped mangrove extent from Global Mangrove Watch' },
  ]

  return (
    <section className="metrics" aria-labelledby="metrics-heading">
      <div className="metrics-inner">
        <div className="section-header">
          <span className="section-eyebrow">Reference results</span>
          <h2 id="metrics-heading" className="section-title">
            Indus Delta reference results
          </h2>
          <p className="section-desc">
            Sample outputs for the Indus Delta, Pakistan only — derived from processing
            GEDI L2A footprints over verified Global Mangrove Watch polygons.
            These values do not apply to Abu Dhabi or custom AOIs.
          </p>
        </div>

        <div className="metrics-grid">
          {metrics.map((m) => (
            <div className="metric-card" key={m.desc}>
              <div className="metric-value">
                {m.value}
                {m.unit && <span className="metric-unit">{m.unit}</span>}
              </div>
              <p className="metric-desc">{m.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function RegionSummary() {
  const regions = [
    {
      name: 'Indus Delta, Pakistan',
      aoi: '[66.5, 23.5, 68.5, 24.8]',
      dates: '2020-01-01 to 2020-04-01',
      gmw: 'Project-owned GMW asset (IndusDelta)',
      note: null,
    },
    {
      name: 'Abu Dhabi, United Arab Emirates',
      aoi: '[54.32, 24.40, 54.52, 24.55]',
      dates: '2019-01-01 to 2021-12-31',
      gmw: 'Project-owned GMW asset (AbuDhabi v2)',
      note: null,
    },
    {
      name: 'Custom AOI',
      aoi: 'User-drawn polygon',
      dates: 'User-selected',
      gmw: 'Configured global GMW dataset',
      note: 'An identical polygon submitted as Custom AOI uses the global GMW source and may therefore produce different results from a predefined region using its own project asset.',
    },
  ]

  return (
    <section className="region-summary" aria-labelledby="regions-heading">
      <div className="region-summary-inner">
        <div className="section-header">
          <span className="section-eyebrow">Study regions</span>
          <h2 id="regions-heading" className="section-title">Configured study regions</h2>
          <p className="section-desc">
            Predefined regions use their verified server-side GMW assets.
            The Analysis page lets you select a region or draw a custom polygon.
          </p>
        </div>

        <div className="region-cards">
          {regions.map((r) => (
            <article className="region-card" key={r.name}>
              <h3 className="region-card-name">{r.name}</h3>
              <dl className="region-card-dl">
                <div className="region-card-row">
                  <dt>AOI</dt>
                  <dd><code>{r.aoi}</code></dd>
                </div>
                <div className="region-card-row">
                  <dt>Default dates</dt>
                  <dd>{r.dates}</dd>
                </div>
                <div className="region-card-row">
                  <dt>GMW source</dt>
                  <dd>{r.gmw}</dd>
                </div>
              </dl>
              {r.note && <p className="region-card-note">{r.note}</p>}
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function HowItWorks() {
  const steps = [
    {
      icon: <PinIcon />,
      title: 'Select study area and dates',
      desc: 'Define a geographic bounding box and temporal window for your mangrove region of interest.',
    },
    {
      icon: <SatelliteIcon />,
      title: 'Retrieve GEDI L2A & GMW data',
      desc: 'Download and filter GEDI canopy-height footprints and Global Mangrove Watch polygons from Earth Engine.',
    },
    {
      icon: <FormulaIcon />,
      title: 'Apply biomass & carbon equations',
      desc: 'Convert RH98 canopy height to above-ground and below-ground biomass, then to carbon stocks.',
    },
    {
      icon: <ChartIcon />,
      title: 'Explore maps and results',
      desc: 'Visualise spatial carbon distributions, summary statistics and export-ready tables.',
    },
  ]

  return (
    <section className="how-it-works" aria-labelledby="how-heading">
      <div className="how-inner">
        <div className="section-header">
          <span className="section-eyebrow">Workflow</span>
          <h2 id="how-heading" className="section-title">How the analysis works</h2>
          <p className="section-desc">
            Four reproducible steps from raw satellite data to publication-ready carbon estimates.
          </p>
        </div>

        <div className="steps-grid">
          {steps.map((s, i) => (
            <div className="step-card" key={s.title}>
              <div className="step-number" aria-hidden="true">{String(i + 1).padStart(2, '0')}</div>
              <div className="step-icon" aria-hidden="true">{s.icon}</div>
              <h3 className="step-title">{s.title}</h3>
              <p className="step-desc">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function SciMethod() {
  return (
    <section id="methodology" className="sci-method" aria-labelledby="sci-heading">
      <div className="sci-inner">
        <div className="section-header">
          <span className="section-eyebrow">Science</span>
          <h2 id="sci-heading" className="section-title">Scientific method</h2>
          <p className="section-desc">
            Allometric equations linking GEDI canopy height to above- and below-ground biomass,
            then to ecosystem carbon stocks.
          </p>
        </div>

        <div className="formula-grid">
          <div className="formula-card">
            <div className="formula-step-label">Step 1 — Above-ground biomass</div>
            <div className="formula-eq">
              <span className="var">AGB</span>
              <span className="op"> = </span>
              <span className="const">10</span>
              <span className="op"> × </span>
              <span className="var">RH98</span>
            </div>
            <p className="formula-desc">
              RH98 (98th-percentile relative height) from GEDI L2A is used as a
              proxy for canopy height. Coefficient 10 converts metres to Mg/ha.
            </p>
          </div>

          <div className="formula-card">
            <div className="formula-step-label">Step 2 — Below-ground biomass</div>
            <div className="formula-eq">
              <span className="var">BGB</span>
              <span className="op"> = </span>
              <span className="const">0.49</span>
              <span className="op"> × </span>
              <span className="var">AGB</span>
            </div>
            <p className="formula-desc">
              Root-to-shoot ratio of 0.49 is applied to AGB to estimate
              below-ground biomass in the root and peat layers.
            </p>
          </div>

          <div className="formula-card">
            <div className="formula-step-label">Step 3 — Carbon stock</div>
            <div className="formula-eq">
              <span className="var">Carbon</span>
              <span className="op"> = </span>
              <span className="const">0.5</span>
              <span className="op"> × (</span>
              <span className="var">AGB</span>
              <span className="op"> + </span>
              <span className="var">BGB</span>
              <span className="op">)</span>
            </div>
            <p className="formula-desc">
              Carbon fraction of 0.5 converts total dry biomass to carbon
              mass (Mg C/ha), following IPCC guidelines.
            </p>
          </div>
        </div>

        <p className="sci-note">
          <strong>Backend processing:</strong> All spatial queries, GEDI footprint filtering and
          biomass calculations will be executed server-side using the{' '}
          <strong>Google Earth Engine Python API</strong> via the FastAPI backend.
          Raw results are returned as GeoJSON and summary statistics for rendering in the frontend.
        </p>
      </div>
    </section>
  )
}

function Datasets() {
  const datasets = [
    {
      iconClass: 'icon-gedi',
      icon: <SatelliteIcon />,
      name: 'GEDI L2A',
      source: 'NASA / LPDAAC',
      desc: 'Global Ecosystem Dynamics Investigation LiDAR providing canopy height and vertical structure metrics at 25 m footprints.',
    },
    {
      iconClass: 'icon-s2',
      icon: <MangroveIcon />,
      name: 'Sentinel-2',
      source: 'ESA / Copernicus',
      desc: 'Multispectral optical imagery at 10–20 m resolution. Not used in the current authoritative L2A height-based calculation; retained here as a potential future or experimental input.',
      experimental: true,
    },
    {
      iconClass: 'icon-gmw',
      icon: <MangroveIcon />,
      name: 'Global Mangrove Watch',
      source: 'JAXA / Aberystwyth',
      desc: 'Annual global mangrove extent maps at 25 m resolution derived from SAR backscatter time series.',
    },
    {
      iconClass: 'icon-gee',
      icon: <SatelliteIcon />,
      name: 'Google Earth Engine',
      source: 'Google / Cloud',
      desc: 'Petabyte-scale cloud geospatial platform hosting all datasets and executing server-side spatial analysis workflows.',
    },
  ]

  return (
    <section className="datasets" aria-labelledby="datasets-heading">
      <div className="datasets-inner">
        <div className="section-header">
          <span className="section-eyebrow">Data sources</span>
          <h2 id="datasets-heading" className="section-title">Datasets and platforms</h2>
          <p className="section-desc">
            Open satellite archives combined with cloud-based geospatial computing.
          </p>
        </div>

        <div className="datasets-grid">
          {datasets.map((d) => (
            <article className="dataset-card" key={d.name}>
              <div className={`dataset-icon ${d.iconClass}`} aria-hidden="true">
                {d.icon}
              </div>
              <div className="dataset-body">
                <div className="dataset-name">
                  {d.name}
                  {d.experimental && (
                    <span className="dataset-tag-future" aria-label="future or experimental capability">
                      Future / experimental
                    </span>
                  )}
                </div>
                <div className="dataset-source">{d.source}</div>
                <p className="dataset-desc">{d.desc}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function CTA() {
  return (
    <section className="cta-section" aria-labelledby="cta-heading">
      <div className="cta-inner">
        <h2 id="cta-heading" className="cta-title">
          Ready to explore mangrove carbon stocks?
        </h2>
        <p className="cta-desc">
          Load the analysis dashboard to run your own carbon assessment —
          select Indus Delta, Abu Dhabi, or draw a custom polygon, then configure
          your date range and run live Earth Engine processing.
        </p>
        <Link to="/analysis" className="cta-btn">
          Open the Analysis Dashboard <ArrowIcon />
        </Link>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div>
          <div className="footer-brand-row">
            <span className="footer-brand-icon" aria-hidden="true">
              <MangroveIcon />
            </span>
            <span className="footer-brand-name">Mangrove Carbon Explorer</span>
          </div>
          <p className="footer-disclaimer">
            Built for research and educational purposes. All satellite data,
            equations and results are provided without warranty. Indus Delta reference
            values are derived from the Indus Delta, Pakistan only and do not apply to
            Abu Dhabi or custom AOIs.
          </p>
        </div>

        <div>
          <div className="footer-col-title">Navigation</div>
          <ul className="footer-nav-list">
            <li><Link to="/">Home</Link></li>
            <li><Link to="/analysis">Analysis</Link></li>
            <li><a href="#methodology">Methodology</a></li>
          </ul>
        </div>

        <div>
          <div className="footer-col-title">Data sources</div>
          <ul className="footer-nav-list">
            <li><a href="https://gedi.umd.edu/" target="_blank" rel="noreferrer">GEDI L2A</a></li>
            <li><a href="https://sentinel.esa.int/" target="_blank" rel="noreferrer">Sentinel-2</a></li>
            <li><a href="https://www.globalmangrovewatch.org/" target="_blank" rel="noreferrer">Global Mangrove Watch</a></li>
            <li><a href="https://earthengine.google.com/" target="_blank" rel="noreferrer">Earth Engine</a></li>
          </ul>
        </div>
      </div>

      <div className="footer-bottom">
        <span className="footer-copyright">
          Mangrove Carbon Explorer — Environmental analytics dashboard
        </span>
        <div className="footer-tech-tags" aria-label="Technology stack">
          <span className="footer-tech-tag">React + Vite</span>
          <span className="footer-tech-tag">FastAPI</span>
          <span className="footer-tech-tag">GEDI L2A</span>
          <span className="footer-tech-tag">GEE</span>
        </div>
      </div>
    </footer>
  )
}

/* ─── Page root ─────────────────────────────────────────────────────────── */
export default function Home() {
  return (
    <div className="home-page">
      <Navbar />
      <main>
        <Hero />
        <MetricCards />
        <RegionSummary />
        <HowItWorks />
        <SciMethod />
        <Datasets />
        <CTA />
      </main>
      <Footer />
    </div>
  )
}
