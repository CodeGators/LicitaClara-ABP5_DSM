import { useEffect, useRef } from 'react'

const selector = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'

// Shared by help and the mobile navigation drawer; background inertness is owned by Layout.
export default function useDialogFocus(ref, active, onClose, fallbackRef) {
  const close = useRef(onClose)
  close.current = onClose
  useEffect(() => {
    if (!active || !ref.current) return
    const root = ref.current
    const previous = document.activeElement
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const controls = () => [...root.querySelectorAll(selector)].filter(el => el.getClientRects().length && !el.closest('[hidden],[inert]'))
    const focusFirst = () => (controls()[0] || root).focus({ preventScroll: true })
    focusFirst()
    const keydown = event => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close.current(); return }
      if (event.key !== 'Tab') return
      const list = controls()
      const first = list[0] || root
      const last = list.at(-1) || root
      if (!list.length || (!event.shiftKey && (document.activeElement === last || document.activeElement === root)) || (event.shiftKey && (document.activeElement === first || document.activeElement === root))) {
        event.preventDefault(); (event.shiftKey ? last : first).focus()
      }
    }
    const focusin = event => { if (!root.contains(event.target)) focusFirst() }
    document.addEventListener('keydown', keydown, true)
    document.addEventListener('focusin', focusin)
    return () => {
      document.removeEventListener('keydown', keydown, true)
      document.removeEventListener('focusin', focusin)
      document.body.style.overflow = overflow
      const target = previous && previous !== document.body && previous.isConnected && previous.getClientRects().length ? previous : fallbackRef?.current
      if (target && !target.closest('[inert]')) target.focus({ preventScroll: true })
    }
  }, [ref, active, fallbackRef])
}
