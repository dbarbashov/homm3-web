"""Run browser audio clocks without audible output in Chromium and WebKit."""


def use_silent_audio(page, device_sink=False):
    page.add_init_script("const testDeviceSink = " + ('true;' if device_sink else 'false;') + """
        const NativeAudioContext = window.AudioContext || window.webkitAudioContext;
        if (NativeAudioContext) {
            const silentSink = !testDeviceSink && 'setSinkId' in NativeAudioContext.prototype;
            const SilentAudioContext = class extends NativeAudioContext {
                constructor(options = {}) {
                    super(silentSink ? {...options, sinkId: {type: 'none'}} : options);
                    if (!silentSink) {
                        const output = super.destination;
                        const mute = this.createGain();
                        mute.gain.value = 0;
                        mute.connect(output);
                        Object.defineProperty(this, 'destination', {get: () => mute});
                    }
                }
            };
            window.AudioContext = SilentAudioContext;
            if (window.webkitAudioContext) window.webkitAudioContext = SilentAudioContext;
        }
        const play = HTMLMediaElement.prototype.play;
        HTMLMediaElement.prototype.play = function(...args) {
            this.muted = true;
            this.volume = 0;
            return play.apply(this, args);
        };
    """)
