"""Exercise the real duration lookup with UBSan, including the unlimited sentinel."""
from pathlib import Path
import argparse,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/portable-source/src/singleselectionwindow.cpp');args=p.parse_args()
s=args.source.read_text();table=re.search(r'static const int g_turnDurationMinutes\[10\] = \{.*?\};',s,re.S).group();start=s.index('static inline void updateTurnDuration()');end=s.index('\n}',start)+2;body=s[start:end]
out=ROOT/'build/turn-duration-regression';out.mkdir(parents=True,exist_ok=True)
source='''#include <cassert>
#include <cstdio>
struct Game { struct { signed char m_turnDuration; } m_setup; } game;
Game* g_game = &game;
struct Timer { unsigned long ms; void setDuration(unsigned long value) { ms = value; } } g_turnDuration;
'''+table+'\n'+body+'''
int main() {
    const unsigned long expected[] = {60000,120000,240000,360000,480000,600000,900000,1200000,1500000,1800000};
    for (int index = 0; index < 10; ++index) {
        game.m_setup.m_turnDuration = index; updateTurnDuration();
        assert(g_turnDuration.ms == expected[index]);
    }
    game.m_setup.m_turnDuration = 10; updateTurnDuration();
    assert(g_turnDuration.ms == 0);
    for (int index = -128; index <= 127; ++index) {
        if (index >= 0 && index < 10) continue;
        game.m_setup.m_turnDuration = index; updateTurnDuration();
        assert(g_turnDuration.ms == 0);
    }
    puts("PASS: all ten finite limits, unlimited, every invalid signed-byte value");
}
'''
(out/'main.cpp').write_text(source)
subprocess.run(['clang++','-std=c++14','-O1','-fsanitize=undefined','-fno-sanitize-recover=all',str(out/'main.cpp'),'-o',str(out/'check')],check=True)
subprocess.run([str(out/'check')],check=True)
