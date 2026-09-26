import type { ButtonHTMLAttributes, ReactNode } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost'
export type ButtonSize = 'md' | 'lg'

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  children: ReactNode
}

/** H13 primitive: the one primary action is `primary` + `lg`; the rest are secondary/ghost. */
export function Button({ variant = 'secondary', size = 'md', loading = false, disabled, children, style, ...rest }: ButtonProps) {
  const big = size === 'lg'
  const base: Record<string, string | number> = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderRadius: 6,
    fontSize: big ? 16 : 14,
    fontWeight: 600,
    padding: big ? '12px 20px' : '8px 14px',
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    opacity: disabled || loading ? 0.6 : 1,
    border: '1px solid transparent',
  }
  const tones: Record<ButtonVariant, Record<string, string>> = {
    primary: { background: 'var(--ink)', color: 'var(--bg)', borderColor: 'var(--ink)' },
    secondary: { background: 'var(--surface)', color: 'var(--ink)', borderColor: 'var(--line)' },
    ghost: { background: 'transparent', color: 'var(--ink)', borderColor: 'transparent' },
  }
  return (
    <button type="button" disabled={disabled || loading} aria-busy={loading} style={{ ...base, ...tones[variant], ...style }} {...rest}>
      {loading ? 'Saving…' : children}
    </button>
  )
}
