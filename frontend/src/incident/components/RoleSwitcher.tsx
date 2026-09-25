import { roleLabel, roles } from '../format'
import type { Role } from '../types'

export type ViewRole = Role | 'All'

export function RoleSwitcher({ value, onChange }: { value: ViewRole; onChange: (role: ViewRole) => void }) {
  return <div className="flex flex-wrap gap-1" role="group" aria-label="Action owner">
    {(['All', ...roles] as ViewRole[]).map((role) => <button key={role} type="button" onClick={() => onChange(role)}
      title={role === 'All' ? 'All roles' : roleLabel[role]}
      className={`border px-2.5 py-1 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy ${value === role ? 'border-navy bg-navy text-white' : 'border-line bg-white text-muted hover:bg-slate-50'}`}>
      {role}
    </button>)}
  </div>
}
