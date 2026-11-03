// Marca: janela aberta (colchete) + 3 colunas + marcador verde-petróleo
export function Mark({ size = 32, bracket = '#102D46', bars = '#617587' }) {
  return (
    <svg width={size} height={size} viewBox="18 18 68 68" aria-hidden="true">
      <path d="M23 23h56.6v4.7H27.7V79.6H23z" fill={bracket} />
      <rect x="34.8" y="59.8" width="5.9" height="15.2" rx="1.2" fill={bars} />
      <rect x="45.3" y="46.9" width="5.9" height="28.1" rx="1.2" fill={bars} />
      <rect x="55.9" y="34" width="5.9" height="41" rx="1.2" fill={bars} />
      <rect x="67.6" y="43.4" width="12.9" height="7.6" rx="1.2" fill="#087F83" />
    </svg>
  )
}
export default function Logo({ dark = true, size = 20 }) {
  const c = dark ? '#fff' : '#102D46'
  return (
    <div className="logo" style={{ color: c, fontSize: size }}>
      <Mark size={size * 1.6} bracket={c} bars={dark ? '#B8CCD9' : '#617587'} />
      <div><b>Licita</b> <span>Clara</span></div>
    </div>
  )
}
