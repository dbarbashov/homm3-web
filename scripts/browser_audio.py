"""Keep headless Chromium's real audio graph independent of the OS output device."""


def use_silent_audio(page):
    page.add_init_script("""
        if ('setSinkId' in AudioContext.prototype) {
            const NativeAudioContext = AudioContext;
            window.AudioContext = class extends NativeAudioContext {
                constructor(options = {}) { super({...options, sinkId: {type: 'none'}}); }
            };
        }
    """)
