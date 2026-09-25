import sys, json
sys.path.insert(0, ".")
from incident.scenario_loader import ScenarioLoader, ScenarioSpec
from incident.signals import SignalGenerator
from incident.clock import TICK_S
from incident.contracts import Effect

BASE = json.load(open("incident/scenarios/C1_black_tuesday.json"))

def build(px_track=None, capacity=None, slippage=None, fund=None):
    data = json.loads(json.dumps(BASE))
    if px_track is not None:
        data["tracks"]["PX"] = px_track
    if capacity is not None:
        data["book"]["liq_capacity_per_min"] = capacity
    if slippage is not None:
        data["book"]["slippage"] = slippage
    if fund is not None:
        data["book"]["insurance_fund_usd"] = fund
    return ScenarioLoader(ScenarioSpec.model_validate(data))

def replay(loader, upto=1700, effects=None, approve_at=None):
    gen = SignalGenerator(loader)
    t = -120
    rows = {}
    eff = []
    while t <= upto:
        if effects and approve_at is not None and t == approve_at:
            eff = [(e, approve_at) for e in effects]
        rows[t] = gen.step(t, eff)
        t += TICK_S
    return rows

def trace(rows, lo=-2, hi=27):
    for m in range(lo, hi):
        tt = m*60
        if tt not in rows: continue
        f = rows[tt]
        print(f"T{m:+3d} t={tt:5d} PX5M={f.values['PX_CHG_5M']:7.2f} LIQ={f.values['LIQ_RATE']:7.1f} LAR={f.values['LAR']:5.2f} fund={f.values['INS_FUND_PCT']:6.2f} bad={f.values['BAD_DEBT_RATE']:6.3f}")

if __name__ == "__main__":
    loader = build()
    rows = replay(loader)
    trace(rows)

def check_no_action(rows):
    out = []
    def g(t, code):
        return rows[t].values[code]
    # target 1: pre-roll normal
    # target 2: warning by T+2
    liq2 = g(120, "LIQ_RATE")
    out.append(("T+2 LIQ>=100", liq2 >= 100, liq2))
    # target 3: T+2..T+11 LIQ in [100,290], no critical, fund not too drained
    band_ok = True
    for m in range(2, 12):
        t = m*60
        v = g(t, "LIQ_RATE")
        if not (100 <= v <= 290):
            band_ok = False
            out.append((f"T+{m} LIQ in[100,290]", False, v))
    out.append(("T+2..11 LIQ band overall", band_ok, None))
    # target 4
    liq14 = g(840, "LIQ_RATE"); fund14 = g(840, "INS_FUND_PCT")
    out.append(("T+14 LIQ in[350,500]", 350<=liq14<=500, liq14))
    out.append(("T+14 fund in[35,45]", 35<=fund14<=45, fund14))
    # target 5
    ok5 = True
    for m in range(15, 19):
        t = m*60
        v = g(t, "LIQ_RATE")
        if v < 150:
            ok5 = False
            out.append((f"T+{m} LIQ>=150", False, v))
    out.append(("T+15..18 LIQ>=150 overall", ok5, None))
    # target 6: fund <25 between T+20 and T+26
    cross = None
    for t in sorted(rows):
        if t < 0: continue
        if g(t, "INS_FUND_PCT") < 25:
            cross = t
            break
    out.append(("fund<25 crossing in [1200,1560]", cross is not None and 1200<=cross<=1560, cross))
    return out

def check_reduce_only(rows):
    out = []
    funds = [f.values["INS_FUND_PCT"] for f in rows.values()]
    out.append(("never EMERGENCY-level fund(<25)", min(funds) >= 25, min(funds)))
    out.append(("fund>=28 (target7)", min(funds) >= 28, min(funds)))
    liq45 = rows[2700].values["LIQ_RATE"]
    out.append(("T+45 LIQ<50", liq45 < 50, liq45))
    return out

from incident.contracts import Effect as _Effect
REDUCE_ONLY = [
    (_Effect(signal="sim.new_exposure", op="set", value=0.0, ramp_s=60), 1080),
    (_Effect(signal="LIQ_RATE", op="mult", value=0.6, ramp_s=120), 1080),
]

def replay_reduce_only(loader, upto=3360):
    return replay(loader, upto=upto, effects=[e for e,_ in REDUCE_ONLY], approve_at=1080)
