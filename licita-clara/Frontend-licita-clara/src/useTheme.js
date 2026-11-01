import { useEffect, useState } from 'react'

export default function useTheme() {
  const [tema, setTema] = useState(() => document.documentElement.dataset.theme || 'light')
  useEffect(() => {
    document.documentElement.dataset.theme = tema
    try { localStorage.setItem('lc_tema', tema) } catch { /* ignora */ }
  }, [tema])
  return [tema, () => setTema(t => (t === 'dark' ? 'light' : 'dark'))]
}
