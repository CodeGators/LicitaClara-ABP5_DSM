import { useEffect, useRef } from 'react'

const options = [
  ['menor_anomalia', 'Menor anomalia', 'green'],
  ['anomalia_intermediaria', 'Anomalia intermediária', 'yellow'],
  ['maior_anomalia', 'Maior anomalia', 'red'],
  ['requer_validacao', 'Requer validação', 'neutral'],
  ['sem_analise', 'Sem análise disponível', 'neutral'],
]

export default function SignalFilter({ value = [], onChange }) {
  const ref = useRef(null)
  useEffect(() => {
    const closeOutside = event => {
      if (ref.current && !ref.current.contains(event.target)) ref.current.open = false
    }
    document.addEventListener('click', closeOutside)
    return () => document.removeEventListener('click', closeOutside)
  }, [])
  const toggle = key => {
    const next = value.includes(key) ? value.filter(v => v !== key) : [...value, key]
    onChange(next)
  }
  const selected = options.find(([key]) => value.length === 1 && value[0] === key)
  return <fieldset className="field signal-filter"><legend>Sinalização do item</legend>
    <details ref={ref} onKeyDown={e => { if (e.key === 'Escape') { e.preventDefault(); ref.current.open = false; ref.current.querySelector('summary').focus() } }}>
      <summary className="select">{selected ? <><span className={`signal-dot ${selected[2]}`} aria-hidden="true" />{selected[1]}</> : value.length ? `${value.length} opções selecionadas` : 'Todas as sinalizações'}</summary>
      <div className="signal-options">
        {options.map(([key, label, color]) => <label key={key}><input type="checkbox" checked={value.includes(key)} onChange={() => toggle(key)} /><span className={`signal-dot ${color}`} aria-hidden="true" />{label}</label>)}
      </div>
    </details>
  </fieldset>
}
