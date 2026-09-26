import type { TeamMember } from '../types'

const marker: Record<string, string> = { Active: 'bg-green-500', Available: 'bg-green-500', Busy: 'bg-amber-500', Standby: 'bg-slate-400' }

export function TeamStatus({ team }: { team: TeamMember[] }) {
  return <section className="border border-line bg-white p-3" aria-label="Team status"><h2 className="text-xs font-bold uppercase tracking-[0.13em]">Team status</h2><div className="mt-2 space-y-2">{team.map((member) => <div key={member.id} className="border-l-2 border-line pl-2"><div className="flex items-center gap-1.5 text-xs"><span className={`h-2 w-2 rounded-full ${marker[member.status] ?? 'bg-slate-400'}`} /><strong>{member.id}</strong><span>— {member.title}</span><span className="ml-auto text-[10px] text-muted">{member.status}</span></div><p className="mt-0.5 text-[10px] text-muted">{member.responsibility}</p></div>)}</div></section>
}
