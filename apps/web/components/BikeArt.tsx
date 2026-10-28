export function BikeArt({ variant = 0 }: { variant?: number }) {
  return (
    <div className={`bike-art art-${variant % 3}`} aria-label="Stylized motorcycle illustration" role="img">
      <span className="art-orbit" />
      <svg viewBox="0 0 360 185" fill="none" aria-hidden="true" className="bike-vector">
        <ellipse cx="180" cy="165" rx="151" ry="10" fill="#101f2e" opacity=".16" />
        <circle cx="79" cy="132" r="41" stroke="#121d2c" strokeWidth="14" />
        <circle cx="280" cy="132" r="41" stroke="#121d2c" strokeWidth="14" />
        <circle cx="79" cy="132" r="18" stroke="#a6b1ba" strokeWidth="5" />
        <circle cx="280" cy="132" r="18" stroke="#a6b1ba" strokeWidth="5" />
        <path d="M80 132L138 75L215 132L80 132M138 75L164 132H215L250 73L280 132M164 132L138 75" stroke="#1b2838" strokeWidth="9" strokeLinejoin="round" />
        <path d="M127 72C148 52 205 50 229 68C214 91 180 101 146 89Z" fill="#1d3345" />
        <path d="M131 71C144 54 201 53 221 68" stroke="#f2bb6d" strokeWidth="8" strokeLinecap="round" />
        <path d="M195 96L216 117L170 134" stroke="#253445" strokeWidth="16" strokeLinejoin="round" />
        <path d="M144 61L113 58" stroke="#243545" strokeWidth="11" strokeLinecap="round" />
        <path d="M242 67L259 36L285 37" stroke="#263646" strokeWidth="7" strokeLinecap="round" />
        <path d="M261 37L246 25" stroke="#263646" strokeWidth="5" strokeLinecap="round" />
        <path d="M284 90L297 55" stroke="#263646" strokeWidth="8" strokeLinecap="round" />
        <circle cx="298" cy="54" r="11" fill="#f4ce82" stroke="#1b2838" strokeWidth="4" />
      </svg>
      <span className="art-caption">INSPECTED • VERIFIED</span>
    </div>
  );
}
