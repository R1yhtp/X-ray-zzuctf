'use strict';
const $ = id => document.getElementById(id);
let totalRuns=0;
const urls=[];
function notice(text,error=false){$('message').textContent=text;$('message').classList.toggle('error',error);}
function selected(){return [...document.querySelectorAll('#probes input:checked')].map(x=>x.value);}
function countProbes(){const n=selected().length;$('probe-count').textContent=`${n} / 4`;for(const e of document.querySelectorAll('#probes input'))e.disabled=n>=4&&!e.checked;}
async function init(){
 try{
  const r=await fetch('/api/info');if(!r.ok)throw new Error('板卡未连接');const info=await r.json();
  $('instance').textContent=`BOARD / ${info.instance.slice(0,8).toUpperCase()}`;
  for(const sig of info.signals){const label=document.createElement('label');label.className='probe';const box=document.createElement('input');box.type='checkbox';box.value=sig.name;box.checked=['tx_valid','tx_ready','tx_addr','tx_data'].includes(sig.name);box.addEventListener('change',countProbes);const name=document.createElement('span');name.textContent=sig.name;const width=document.createElement('small');width.textContent=`${sig.width}b`;label.append(box,name,width);$('probes').append(label);}countProbes();notice('板卡就绪。配置探针后开始采集。');
 }catch(e){notice(e.message,true);$('capture').disabled=true;}
}
$('trigger').addEventListener('change',()=>{$('trigger-note').textContent={activity:'tx_valid 有效时记录候选事件；每次采集从同一上电状态重放。',clock:'连续记录每个时钟周期；起始位置以复位释放后的候选事件计。',vblank:'场同步有效期间记录候选事件；起始位置在筛选后的事件序列中计。'}[$('trigger').value];});
$('capture').addEventListener('click',async()=>{
 const config={probes:selected(),trigger:$('trigger').value,start:Number($('start').value),count:Number($('count').value)};
 if(!config.probes.length)return notice('请至少选择一组探针。',true);
 if(!Number.isInteger(config.start)||config.start<0||config.start>32768||!Number.isInteger(config.count)||config.count<1||config.count>1024)return notice('起始事件应为 0～32768，采样深度应为 1～1024。',true);
 const btn=$('capture');btn.disabled=true;btn.textContent='正在运行采集…';notice('正在重放板卡并锁存信号。');
 try{
  const r=await fetch('/api/capture',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(config)});
  if(!r.ok){const err=await r.json();throw new Error(err.error||'采集失败');}
  const blob=await r.blob();const url=URL.createObjectURL(blob);urls.push(url);
  const row=document.createElement('div');row.className='record';const icon=document.createElement('span');icon.className='icon';icon.textContent='≋';const desc=document.createElement('div');const title=document.createElement('p');title.textContent=`CAPTURE ${String(++totalRuns).padStart(2,'0')} / ${config.trigger}`;const detail=document.createElement('small');detail.textContent=`事件 ${config.start} 起 · 最多 ${config.count} 点 · ${config.probes.join(' / ')}`;desc.append(title,detail);const link=document.createElement('a');link.href=url;link.download=`capture-${config.trigger}-${config.start}.zip`;link.textContent='下载 ZIP ↓';row.append(icon,desc,link);$('history').prepend(row);$('empty').hidden=true;$('run-count').textContent=`本次会话 · ${totalRuns} 次`;
  while($('history').children.length>20){const last=$('history').lastElementChild;URL.revokeObjectURL(last.querySelector('a').href);last.remove();}
  notice('采集完成。下载 ZIP 后检查波形与 acquisition.json。');
 }catch(e){notice(e.message,true);}finally{btn.disabled=false;btn.textContent='开始采集 ↗';}
});
window.addEventListener('beforeunload',()=>urls.forEach(URL.revokeObjectURL));
init();
