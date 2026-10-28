"""Profile a ranged battle using original UI input and optional CPU throttling.

The fixture uses the original nwczion cheat to build a Conflux town, then
upgrades Air Elementals to Storm Elementals through the recruitment UI.
No game memory is written. Requires locally supplied original game resources.
Set CPU=4 to emulate a slower CPU; RUN chooses the output directory.
"""

from pathlib import Path
from browser_audio import use_silent_audio
from playwright.sync_api import sync_playwright
import json, os, time, collections

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test-results/battle-performance" / os.getenv("RUN", "combat")
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={"width": 1200, "height": 900})
    use_silent_audio(page)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script(
        """
        window.homm3CombatTrace=[];
        window.perf={frames:[],tasks:[],sounds:[],uploads:[]};
        let last;
        function tick(t){
            if(last)perf.frames.push([t,t-last]);
            last=t;requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
        new PerformanceObserver(l=>l.getEntries().forEach(e=>
            perf.tasks.push({start:e.startTime,duration:e.duration})
        )).observe({type:'longtask'});
        for(const type of [WebGLRenderingContext,WebGL2RenderingContext]){
            const orig=type.prototype.texSubImage2D;
            type.prototype.texSubImage2D=function(...args){
                perf.uploads.push(performance.now());return orig.apply(this,args);
            };
        }
        """
    )
    c = page.locator("#canvas")

    def screen(s):
        page.wait_for_function(
            "(s)=>window.homm3PortDiagnostics?.screen===s", arg=s, timeout=90000
        )

    def click(x, y):
        box = c.bounding_box()
        c.click(position={"x": x * box["width"] / 800, "y": y * box["height"] / 600})

    page.goto(os.getenv("SITE_URL", "http://127.0.0.1:8783") + "/port/game.html?hd=0")
    page.locator("#start").click()
    screen("main")
    c.press("n")
    screen("new")
    c.press("s")
    screen("scenarios")
    c.press("b")
    page.wait_for_timeout(4000)
    c.press("Enter")
    screen("adventure")
    page.wait_for_timeout(1000)
    # Original cheat builds the town, then upgrade the visiting hero's Air Elementals through UI.
    c.press("Tab")
    c.press_sequentially("nwczion", delay=30)
    c.press("Enter")
    page.wait_for_timeout(500)
    c.dblclick(
        position={
            "x": 770 * c.bounding_box()["width"] / 800,
            "y": 231 * c.bounding_box()["height"] / 600,
        },
        delay=150,
    )
    page.wait_for_timeout(1000)
    page.screenshot(path=str(OUT / "town.png"))
    print(
        "TOWN",
        page.evaluate("({state:homm3GameState,army:homm3Army,hd:homm3HDState})"),
        flush=True,
    )
    c.dblclick(
        position={
            "x": 397 * c.bounding_box()["width"] / 800,
            "y": 515 * c.bounding_box()["height"] / 600,
        },
        delay=100,
    )
    page.wait_for_timeout(400)
    c.press("u")
    page.wait_for_timeout(300)
    c.press("Enter")
    page.wait_for_timeout(500)
    c.press("Escape")
    page.wait_for_timeout(500)
    page.wait_for_function("homm3Army[1].type===127")
    print("Ranged army ready", flush=True)
    for key in ["ArrowDown", "ArrowDown", "End"]:
        c.press(key)
        page.wait_for_timeout(1700)
    page.wait_for_function("homm3GameState.combat===1")
    page.wait_for_timeout(5000)
    page.screenshot(path=str(OUT / "battle.png"))
    page.evaluate(
        """()=>{
            const load=homm3Sfx.load,play=homm3Sfx.play,clips=new Map;
            homm3Sfx.load=function(id,name,heap){
                clips.set(id,name);return load.call(this,id,name,heap);
            };
            homm3Sfx.play=function(slot,id,loops,volume){
                perf.sounds.push({at:performance.now(),slot,id,loops,name:clips.get(id)});
                return play.call(this,slot,id,loops,volume);
            };
            const push=homm3CombatTrace.push;
            homm3CombatTrace.push=function(e){
                if(e.phase==='shot-end'){
                    const shot=perf.sounds.findLast(s=>s.name==='storshot.82M');
                    e.audioTailPlaying=!!shot&&homm3Sfx.playing(shot.slot);
                    e.audioContext=homm3Music.context().state;
                    e.audioTime=homm3Music.context().currentTime;
                }
                return push.call(this,e);
            };
        }"""
    )
    if os.getenv("FAST"):
        click(27, 580)
        page.wait_for_timeout(300)
        click(345, 325)
        c.press("Enter")
        page.wait_for_timeout(500)
        page.wait_for_function("homm3Settings.combatSpeed===2")
    cdp = page.context.new_cdp_session(page)
    cdp.send("Profiler.enable")
    cdp.send("Profiler.setSamplingInterval", {"interval": 1000})
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": int(os.getenv("CPU", "1"))})
    cdp.send("Profiler.start")
    start = page.evaluate("performance.now()")
    for _ in range(8):
        if page.evaluate("homm3GameState.autoCombat===1"):
            break
        click(178, 580)
        page.wait_for_timeout(500)
    page.mouse.move(5, 5)
    page.wait_for_function("homm3GameState.autoCombat===1")
    deadline = time.monotonic() + int(os.getenv("SECONDS", "90"))
    while (
        time.monotonic() < deadline
        and page.evaluate("homm3PortDiagnostics.screen") != "combat-results"
    ):
        page.wait_for_timeout(1000)
    profile = cdp.send("Profiler.stop")["profile"]
    (OUT / "cpu.json").write_text(json.dumps(profile))
    result = page.evaluate(
        "(start)=>({start,elapsed:performance.now()-start,frames:perf.frames.filter(x=>x[0]>=start),tasks:perf.tasks.filter(x=>x.start>=start),sounds:perf.sounds,uploads:perf.uploads.filter(x=>x>=start),settings:homm3Settings,markers:window.homm3CombatTrace,game:homm3GameState,screen:homm3PortDiagnostics.screen,sfx:homm3Sfx.stats})",
        start,
    )
    result["errors"] = errors
    result["cpuThrottle"] = int(os.getenv("CPU", "1"))
    (OUT / "results.json").write_text(json.dumps(result, indent=2))
    page.screenshot(path=str(OUT / "last.png"))
    counts = collections.Counter()
    nodes = {n["id"]: n for n in profile["nodes"]}
    for i, dt in zip(profile["samples"], profile["timeDeltas"]):
        counts[nodes[i]["callFrame"]["functionName"]] += dt / 1000
    shots = [e for e in result["markers"] if e["phase"] == "shot-end"]
    assert len(shots) >= 3, shots
    assert not any(e["audioTailPlaying"] for e in shots), (
        "Original shot sound wait was bypassed"
    )
    waits = [
        b["at"] - a["at"]
        for a, b in zip(result["markers"], result["markers"][1:])
        if a["phase"] == "shot-animation-end" and b["phase"] == "shot-end"
    ]
    assert len(waits) == len(shots) and min(waits) > 900, waits
    assert result["screen"] == "combat-results", result["screen"]
    assert not errors, errors
    assert result["settings"]["combatSpeed"] == 2, (
        "Fresh preferences should default to fast combat"
    )
    print("TASKS", result["tasks"], flush=True)
    print("TOP", counts.most_common(20), flush=True)
    print("SOUNDS", result["sfx"]["byName"], flush=True)
    b.close()
