import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
const children=[];
function run(command,args){const p=spawn(command,args,{stdio:'inherit'});children.push(p);p.on('error',e=>{console.error(e.message);stop(1);});p.on('exit',code=>stop(code||0));return p;}
let stopping=false;
function stop(code=0){if(stopping)return;stopping=true;for(const p of children)p.kill('SIGTERM');setTimeout(()=>process.exit(code),100);}
process.on('SIGINT',()=>stop());process.on('SIGTERM',()=>stop());
const relay=resolve(process.env.HOMM3_LOBBY_ROOT || '../homm3-lobby','Cargo.toml');
if(existsSync(relay))run('cargo',['run','--locked','--manifest-path',relay]);
else console.log('Starting standalone client. Optional room relay: HOMM3_LOBBY_ROOT=/path/to/homm3-lobby');
run('node',['server.mjs']);
