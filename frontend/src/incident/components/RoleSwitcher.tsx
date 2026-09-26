import { roleLabel } from '../format'
import { teamByRole, teamDotClass } from '../panels'
import type { Role, TeamMember } from '../types'

export type ViewRole = Role | 'All'

/**
 * H14: the role switcher *is* the team panel.
 *
 * `TeamStatus.tsx` is gone — each role button now carries its owner's status
 * dot and name (`IC ● Busy`), which is the only place team status appears
 * (UI_PLAN §3, "Team"). The dot is always paired with the word, so status is
 * never colour alone.
 */
export function RoleSwitcher({ value, onChange, team }: { value: ViewRole; onChange: (role: ViewRole) => void; team?: TeamMember[] }) {
  const byRole = teamByRole(team)
  return <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="View as role">
    {(['All', 'IC', 'TL', 'CS'] as ViewRole[]).map((role) => {
      const member = role === 'All' ? undefined : byRole[role]
      const active = value === role
      return <button key={role} type="button" onClick={() => onChange(role)}
        title={role === 'All' ? 'All roles' : roleLabel[role]}
        aria-pressed={active}
        className="flex items-center gap-1.5 border px-2.5 py-1 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy"
        style={{
          borderColor: active ? 'var(--ink)' : 'var(--line)',
          background: active ? 'var(--ink)' : 'var(--surface)',
          color: active ? 'var(--bg)' : 'var(--ink)',
        }}>
        {role}
        {member && <span className="flex items-center gap-1 font-normal" style={{ opacity: active ? 0.85 : 0.7 }}>
          <span aria-hidden="true" className={`h-2 w-2 rounded-full ${teamDotClass(member.status)}`} />
          {member.status}
        </span>}
      </button>
    })}
  </div>
}
