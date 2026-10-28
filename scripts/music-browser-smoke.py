"""Render the actual Web Audio graph offline; no system audio device is required."""

from pathlib import Path
from playwright.sync_api import sync_playwright
import os, json

ROOT = Path(__file__).resolve().parents[1]
engine = os.getenv("BROWSER", "chromium")
with sync_playwright() as p:
    browser = getattr(p, engine).launch(headless=True)
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.set_content('<button id="canvas">Audio fixture</button>')
    page.evaluate("""()=>{
        window.AudioContext=class extends OfflineAudioContext{
            constructor(){super(2,44100*5,44100);this.renderStarted=false;}
            resume(){return this.renderStarted?super.resume():Promise.resolve();}
        };
    }""")
    page.add_script_tag(path=str(ROOT / "web/port/music.js"))
    result = page.evaluate("""async()=>{
        const music=homm3Music;music.unlock();const ctx=music.context(),starts=[];
        const create=ctx.createBufferSource.bind(ctx);
        ctx.createBufferSource=()=>{
            const node=create(),start=node.start.bind(node);
            node.start=(at,offset)=>{starts.push({at,offset});return start(at,offset)};
            return node;
        };
        ctx.decodeAudioData=async()=>{
            const buffer=ctx.createBuffer(1,44100*10,44100),pcm=buffer.getChannelData(0);
            for(let i=0;i<pcm.length;i++)pcm[i]=.5*Math.sin(2*Math.PI*440*i/44100);
            return buffer;
        };
        window.fetch=async()=>({ok:true,arrayBuffer:async()=>new ArrayBuffer(1)});
        music.configure(['A.mp3','B.mp3']);await music.play('A',0,1);
        let switchedAt,stoppedAt;
        const switchTrack=ctx.suspend(1.2).then(async()=>{
            switchedAt=ctx.currentTime;music.play('B',0,1);
            await ctx.resume();
        });
        // Give the outgoing source's onended event a task turn before resuming.
        const startNew=ctx.suspend(2.2).then(async()=>{
            const deadline=performance.now()+5000;
            while(music.state.track!=='B'){
                if(performance.now()>deadline)throw new Error('Pending music did not start');
                await new Promise(resolve=>setTimeout(resolve,0));
            }
            await ctx.resume();
        });
        const stop=ctx.suspend(3.5).then(async()=>{
            stoppedAt=ctx.currentTime;music.stop();await ctx.resume();
        });
        ctx.renderStarted=true;
        const rendered=await ctx.startRendering();await Promise.all([switchTrack,startNew,stop]);
        const pcm=rendered.getChannelData(0);
        function peak(time){
            let value=0;
            for(let i=Math.floor(time*44100);i<Math.floor((time+.015)*44100);i++)value=Math.max(value,Math.abs(pcm[i]));
            return value;
        }
        const samples=[
            ['fade-in',peak(.25),.15],['steady',peak(1.1),.5],
            ['old-track-fade-out',peak(switchedAt+.25),.35],
            ['new-track-fade-in',peak(starts[1].at+.25),.15],
            ['new-track-steady',peak(starts[1].at+1.1),.5],
            ['stop-fade',peak(stoppedAt+.25),.35],['stopped',peak(stoppedAt+1.1),0]
        ];
        music.close();return {samples,starts,switchedAt,stoppedAt};
    }""")
    for label, peak, expected in result["samples"]:
        assert abs(peak - expected) < 0.005, (label, peak, expected)
    assert result["starts"][1]["at"] >= result["switchedAt"] + 0.89, result
    assert not errors, errors
    output = {
        "passed": True,
        "engine": engine,
        "offline": True,
        **result,
        "errors": errors,
    }
    (ROOT / f"test-results/music-{engine}.json").write_text(
        json.dumps(output, indent=2)
    )
    print(json.dumps(output))
    browser.close()
