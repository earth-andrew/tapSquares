#!/usr/bin/env python3
"""Put the treatments the fitted behavior responds to on a game's ABM interface, each as the
widget that suits its type.

Usage:  python3 add_treatment_sliders.py <path to game version folder, e.g. game_to_abm_workflows/cropraider/v2>

Reads  <ver>/abm/agent_behavior_treatment_ranges.csv  (written by the R notebook; promote it first)
and    <ver>/abm/sessionList_ABM.csv                   (for each widget's starting value),
and edits <ver>/abm/tapSquares_ABM_generator.nlogox in place (a .bak copy is kept the first time).

  numeric      -> slider   (fitted range widened by 50% of its span on each side, so users can step
                            outside the data; the ABM then warns that responses are extrapolated.
                            Whole-number settings get step 1.)
  TRUE/FALSE   -> switch
  categorical  -> chooser  (one choice per level seen in the data)

Every widget's variable AND label is sl_<setting> (NetLogo can derive the variable from the label, so they must match; a label equal to the game's own global, e.g. defendCost, collides with it); the ABM copies session values into it at "Initialize
Session" and applies it at "Setup". Widgets go between buttons 2 and 3; widgets below shift down.
Re-running replaces earlier treatment widgets.
"""
import csv, math, os, re, shutil, sys
from xml.sax.saxutils import quoteattr

H = 44  # vertical space per widget


def nice_step(lo, hi, integer):
    if integer:
        return 1
    span = hi - lo
    return 10 ** math.floor(math.log10(span / 100.0)) if span > 0 else 0.01


def fmt(x):
    x = round(float(x), 10)
    return str(int(x)) if x == int(x) else repr(x)


def tf(v):
    return str(v).strip().upper() == "TRUE"


def build_specs(rows, sess):
    specs = []
    for r in rows:
        v = r["variable"]
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v):
            print(f"skip {v}: name not usable as a widget variable")
            continue
        ty = r.get("type") or "numeric"
        raw = sess[0].get(v, "") if sess else ""
        if ty == "logical":
            specs.append(dict(v=v, kind="switch", on=tf(raw)))
        elif ty == "categorical":
            levels = [l for l in (r.get("levels") or "").split(";") if l != ""]
            if not levels:
                print(f"skip {v}: no levels recorded")
                continue
            specs.append(dict(v=v, kind="chooser", levels=levels, cur=levels.index(raw) if raw in levels else 0))
        else:
            lo, hi = float(r["min_value"]), float(r["max_value"])
            integer = str(r.get("integer_valued", "")).upper() == "TRUE"
            span = hi - lo
            smin, smax = lo - 0.5 * span, hi + 0.5 * span
            if lo >= 0:
                smin = max(0.0, smin)
            step = nice_step(smin, smax, integer)
            if integer:
                smin, smax = math.floor(smin), math.ceil(smax)
            try:
                d = float(raw)
            except ValueError:
                d = (lo + hi) / 2
            specs.append(dict(v=v, kind="slider", lo=smin, hi=smax, d=min(max(d, smin), smax), step=step))
    return specs


def widget_xml(sp, y):
    v = sp["v"]
    if sp["kind"] == "slider":
        return (f'<slider x="10" y="{y}" width="320" height="34" min="{fmt(sp["lo"])}" max="{fmt(sp["hi"])}" '
                f'default="{fmt(sp["d"])}" step="{fmt(sp["step"])}" direction="Horizontal" display="sl_{v}" variable="sl_{v}"></slider>')
    if sp["kind"] == "switch":
        return (f'<switch x="10" y="{y}" width="320" height="34" display="sl_{v}" variable="sl_{v}" '
                f'on="{"true" if sp["on"] else "false"}"></switch>')
    ch = "".join(f'<choice type="string" value={quoteattr(l)}></choice>' for l in sp["levels"])
    return (f'<chooser x="10" y="{y}" width="320" height="40" display="sl_{v}" variable="sl_{v}" '
            f'current="{sp["cur"]}">{ch}</chooser>')


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    ver = sys.argv[1].rstrip("/")
    abm = os.path.join(ver, "abm")
    rng_path = os.path.join(abm, "agent_behavior_treatment_ranges.csv")
    sl_path = os.path.join(abm, "sessionList_ABM.csv")
    nl_path = os.path.join(abm, "tapSquares_ABM_generator.nlogox")
    for p in (rng_path, sl_path, nl_path):
        if not os.path.exists(p):
            sys.exit(f"Missing {p} (knit the notebook and run promote_r_output.sh first)")

    specs = build_specs(list(csv.DictReader(open(rng_path, newline=""))),
                        list(csv.DictReader(open(sl_path, newline=""))))
    if not specs:
        sys.exit("No treatments to add widgets for.")

    s = open(nl_path, encoding="utf-8").read()
    bak = nl_path + ".bak"
    if not os.path.exists(bak):
        shutil.copy(nl_path, bak)

    # remove widgets from an earlier run (their vertical shift is undone by the normalisation below)
    s = re.sub(r'\n    <(slider|switch|chooser) [^\n]*variable="sl_[^"]*"[^\n]*</\1>', "", s)
    wl = re.search(r"<widgets>(.*?)</widgets>", s, re.S)
    block = wl.group(1)
    yre = r'(<[a-z]+ [^>]*?x="10" [^>]*?)y="(\d+)"'
    setup = re.search(r'<button x="10"[^>]*?y="(\d+)"[^>]*?display="3\. Setup"', block)
    if not setup:
        sys.exit("Could not find the '3. Setup' button in the interface.")
    y0 = int(setup.group(1))
    # normalise: Setup sits directly below the 'Initialize Session' button
    init = re.search(r'<button x="10"[^>]*?y="(\d+)"[^>]*?display="2\. Initialize Session"', block)
    y_base = int(init.group(1)) + 43 if init else y0
    delta = y_base - y0
    if delta != 0:
        block = re.sub(yre, lambda m: f'{m.group(1)}y="{int(m.group(2)) + delta}"' if int(m.group(2)) >= y0 else m.group(0), block)
    y0 = y_base
    block = re.sub(yre, lambda m: f'{m.group(1)}y="{int(m.group(2)) + H * len(specs)}"' if int(m.group(2)) >= y0 else m.group(0), block)
    new = "".join(f"\n    {widget_xml(sp, y0 + H * k)}" for k, sp in enumerate(specs))
    btn = re.search(r'\n\s*<button x="10"[^>]*?display="3\. Setup"', block)
    block = block[:btn.start()] + new + block[btn.start():]
    s = s[:wl.start(1)] + block + s[wl.end(1):]
    open(nl_path, "w", encoding="utf-8").write(s)
    print("added: " + ", ".join(f'{sp["v"]} ({sp["kind"]})' for sp in specs))


if __name__ == "__main__":
    main()
