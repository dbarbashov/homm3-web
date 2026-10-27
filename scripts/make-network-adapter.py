"""Generate explicit unsupported DirectPlay platform entry points, never gameplay rules."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
s=(root/'upstream/homm3-decomp/src/dxplay.cpp').read_text()
# All concrete DirectPlay methods, with signatures recovered upstream.
pattern=r'^((?:unsigned char\*?|unsigned long|void\*?|bool|DPLCONNECTION\*|DPSESSIONDESC2\*|CDPlayConnection\*)\s+)?(CDPlay(?:Lobby)?::(~?\w+)\([^;{}]*\))\s*\{'
methods=[]
for m in re.finditer(pattern,s,re.M):
    ret=(m[1] or '').strip(); sig=m[2].replace('_GUID','GUID'); name=m[3]
    body=''
    if name not in ['CDPlay','CDPlayLobby','~CDPlay','~CDPlayLobby']:
        body='m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER;'
        if ret!='void':body+=' return 0;'
    methods.append((sig,ret,body))
custom=(root/'port/platform/network_methods.inc').read_text()
custom_names=set(re.findall(r'(CDPlay(?:Lobby)?::\w+)\(',custom))
out='// Unsupported legacy modem/IPX/lobby operations fail explicitly.\n'
for sig,ret,body in methods:
    if sig.split('(')[0] not in custom_names and not sig.startswith(('CDPlay::CDPlay','CDPlay::~','CDPlayLobby::CDPlayLobby','CDPlayLobby::~')):
        out+=f'{ret} {sig} {{ {body} }}\n'
(root/'port/platform/network_unsupported.inc').write_text(out)
print(len(methods), 'platform methods inspected')
