export const Head = ({ title, sub, action }) => (
  <div className="head">
    <div><h1>{title}</h1>{sub && <p className="sub">{sub}</p>}</div>
    {action}
  </div>
)
export const Progress = ({ pct, cor = 'var(--petroleo)', max = 100 }) => (
  <div className="bar"><i style={{ width: `${(pct / max) * 100}%`, background: cor }} /></div>
)
