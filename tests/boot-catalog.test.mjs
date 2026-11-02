import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {test} from 'node:test';

test('late remote catalog cannot overwrite a newly selected local installation', async()=>{
  const nodes=new Map(),pending=[];
  const document={querySelector(selector){
    if(!nodes.has(selector))nodes.set(selector,{addEventListener(){}});
    return nodes.get(selector);
  }};
  const window={addEventListener(){},homm3Assets:{fetch(){
    return new Promise(resolve=>pending.push(resolve));
  }}};
  const context=vm.createContext({window,document,location:{pathname:'/port/game.html'}});
  vm.runInContext(fs.readFileSync(new URL('../web/port/boot.js',import.meta.url),'utf8'),context);
  const remote=vm.runInContext('refreshCatalog()',context);
  const local=vm.runInContext('refreshCatalog()',context);
  pending[1]({ok:true,json:async()=>({ready:true,local:true,maps:['Arrogance.h3m'],archives:[],music:[]})});
  await local;
  pending[0]({ok:true,json:async()=>({ready:false,error:'No remote installation'})});
  await remote;
  assert.equal(vm.runInContext('catalog.local',context),true);
  assert.equal(vm.runInContext('catalog.maps[0]',context),'Arrogance.h3m');
  assert.equal(nodes.get('#start').disabled,false);
});
