import sys; sys.path.insert(0,'.')
from incident.scenario_loader import load_scenario
from incident.signals import SignalGenerator
from incident.rules.history import SignalHistory
from incident.rules.classifier import classify
from incident.rules.severity import score
from incident.rules.state_machine import StateMachine
from incident.content.controls import CONTROLS
def run(label, approve=None):
    gen=SignalGenerator(load_scenario('C1')); sm=StateMachine(); h=SignalHistory()
    eff=[]; prev=None; out=[]
    for t in range(-120,3600,2):
        if approve and t==approve[1]: eff=[(e,t) for e in CONTROLS[approve[0]].effects]
        f=gen.step(t,eff); h.add(f); c=classify(f,h); s=score(f,h,c.verdict); st,_=sm.step(t,s,f)
        if getattr(sm,'pending',None) and t%60==0: sm.confirm('IC',t)
        if st!=prev: out.append(f"T{t//60:+d}:{t%60:02d} {st} S={s.score} fund={f.values['INS_FUND_PCT']:.0f} liq={f.values['LIQ_RATE']:.0f} lar={f.values['LAR']:.2f} {c.verdict} {s.overrides}"); prev=st
    print('==',label); print('\n'.join(out))
run('no action'); run('reduce_only@T+18',('reduce_only',1080))
