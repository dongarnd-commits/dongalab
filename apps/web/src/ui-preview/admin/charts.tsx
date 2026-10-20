import React from 'react';
import type {StageCount,OperatorLoad,DailyCount,TimelineWork,HeatCell,HealthMetric} from './types';

const colors=['#246ECA','#37A89B','#F0A743','#8B7ACB','#DA6C7A','#617C9B','#A0ACB9','#62B1DA'];
export const fmt=(x:number|null|undefined)=>x===null||x===undefined?'—':x.toLocaleString('ko-KR');
export const pct=(part:number,total:number)=>total>0?Math.max(0,Math.min(100,(part/total)*100)):0;
type EmptyKind='donut'|'bar'|'trend'|'funnel'|'gantt'|'heatmap'|'resource';
export function EmptyChart({message='데이터 연결 후 표시',kind='trend',labels=[],onSelect}:{message?:string;kind?:EmptyKind;labels?:string[];onSelect?:()=>void}){
 const legend=labels.length?labels:kind==='donut'||kind==='funnel'?['접수','검토','매칭','제안','기업 확인']:kind==='bar'?['진행','대기','완료']:kind==='trend'?['접수','완료']:kind==='gantt'?['계획·진행','완료']:kind==='heatmap'?['검토','매칭','제안']:['CPU','메모리','저장공간'];
 return <div className={'da-empty-visual da-empty-'+kind} data-chart-kind={kind} role={onSelect?"button":undefined} tabIndex={onSelect?0:undefined} aria-label={onSelect?kind+" 차트 상세 이동":undefined} onClick={onSelect} onKeyDown={e=>{if(onSelect&&(e.key==="Enter"||e.key===" ")){e.preventDefault();onSelect();}}}>
 <svg viewBox="0 0 540 190" role="img" aria-label={kind+' 차트 · 측정 데이터 없음'}>
 {kind==='donut'?<><circle cx="140" cy="92" r="62" fill="none" stroke="#e9edf3" strokeWidth="24"/><text x="140" y="100" textAnchor="middle" fill="#7c8ba0" fontSize="24">—</text><text x="275" y="85" fill="#7c8ba0" fontSize="13">집계 전</text><text x="275" y="110" fill="#9ba7b8" fontSize="12">단위: 건 · 비율 미측정</text></>:
 kind==='heatmap'?<>{[0,1,2].map(row=>[0,1,2,3].map(col=><rect key={row+'-'+col} x={90+col*100} y={30+row*43} width="90" height="33" rx="5" fill="#f1f4f8" stroke="#e2e8f0"/>))}<text x="12" y="90" fill="#7c8ba0" fontSize="12">운영자</text><text x="215" y="185" fill="#7c8ba0" fontSize="12">업무 단계 · 건</text></>:
 <><path d="M55 15 V155 H520" fill="none" stroke="#dce3ed"/>{[40,78,116].map(y=><line key={y} x1="55" x2="520" y1={y} y2={y} stroke="#edf1f6" strokeDasharray="4 4"/>)}
 {kind==='bar'||kind==='funnel'?[0,1,2].map((_,i)=><rect key={i} x="78" y={29+i*40} width={kind==='funnel'?370-i*65:400} height="22" rx="5" fill="#f1f4f8"/>):null}
 {kind==='gantt'?[100,200,300,400].map(x=><line key={x} x1={x} x2={x} y1="15" y2="155" stroke="#edf1f6"/>):null}
 <text x="12" y="18" fill="#7c8ba0" fontSize="11">{kind==='resource'?'사용률 %':kind==='gantt'?'업무':'건'}</text><text x="250" y="181" fill="#7c8ba0" fontSize="12">{kind==='gantt'?'확정 시작일 → 마감일':kind==='bar'?'업무량 (건)':kind==='funnel'?'단계 도달 누적 (건)':'측정 시각'}</text>
 <text x="285" y="95" textAnchor="middle" fill="#8796a8" fontSize="12">측정 데이터 없음</text></>}
 </svg><div className="da-chart-legend">{legend.map(l=><span key={l}><i style={{background:'#cbd5e1'}}/>{l}</span>)}</div><p className="da-chart-footnote">{message}</p></div>;
}
export function DonutChart({items,onSelect,emptyLabels}:{items:StageCount[];onSelect?:(stage:string)=>void;emptyLabels?:string[]}){
 const valid=items.filter(x=>Number.isFinite(x.count)&&x.count>=0),total=valid.reduce((a,b)=>a+b.count,0);
 if(!valid.length||total===0)return <EmptyChart kind="donut" onSelect={onSelect?()=>onSelect(''):undefined} labels={emptyLabels} message="단계별 업무 상태의 실제 집계가 필요합니다."/>;
 const r=64,c=2*Math.PI*r;
 return <div className="da-donut-layout"><svg className="da-donut-svg" viewBox="0 0 190 190" role="img" aria-label={'업무 단계별 분포. 총 '+total+'건'}><circle cx="95" cy="95" r={r} fill="none" stroke="#ECF0F5" strokeWidth="23"/>{valid.map((x,i)=>{const length=(x.count/total)*c,at=valid.slice(0,i).reduce((sum,v)=>sum+v.count/total*c,0);return <circle key={x.stage} cx="95" cy="95" r={r} fill="none" stroke={colors[i%colors.length]} strokeWidth="23" strokeDasharray={length+' '+(c-length)} strokeDashoffset={-at} transform="rotate(-90 95 95)" onClick={()=>onSelect?.(x.stage)} className="da-chart-part"><title>{x.label}: {fmt(x.count)}건</title></circle>})}<text x="95" y="89" textAnchor="middle" className="da-donut-total">{fmt(total)}</text><text x="95" y="110" textAnchor="middle" className="da-donut-caption">건</text></svg><div className="da-legend">{valid.map((x,i)=><button key={x.stage} className="da-legend-row" onClick={()=>onSelect?.(x.stage)}><i style={{background:colors[i%colors.length]}}/><span>{x.label}</span><b>{fmt(x.count)}</b><small>{pct(x.count,total).toFixed(1)}%</small></button>)}</div></div>;
}
export function WorkloadBars({items,onSelect}:{items:OperatorLoad[];onSelect?:(id:string)=>void}){
 if(!items.length)return <EmptyChart onSelect={onSelect?()=>onSelect(''):undefined} kind="bar" message="업무량 데이터 연결 후 표시"/>;
 const max=Math.max(1,...items.map(x=>Math.max(0,x.inProgress+x.waiting+x.completed)));
 return <div className="da-workload"><div className="da-chart-legend"><span><i style={{background:'#246ECA'}}/> 진행</span><span><i style={{background:'#F0A743'}}/> 대기</span><span><i style={{background:'#37A89B'}}/> 완료</span></div>{items.slice(0,12).map(x=>{const stack=x.inProgress+x.waiting+x.completed;return <button key={x.operatorId} className="da-workload-row" onClick={()=>onSelect?.(x.operatorId)}><span className="da-workload-label" title={x.operatorName}>{x.operatorName}</span><span className="da-workload-track"><span style={{width:(x.inProgress/max*100)+'%',background:'#246ECA'}} title={'진행 '+x.inProgress}/><span style={{width:(x.waiting/max*100)+'%',background:'#F0A743'}} title={'대기 '+x.waiting}/><span style={{width:(x.completed/max*100)+'%',background:'#37A89B'}} title={'완료 '+x.completed}/></span><b className="da-workload-count">{fmt(stack)}</b></button>})}<div className="da-chart-footnote">진행·대기·완료는 집계 원천에서 서로 중복되지 않는 업무 상태여야 합니다.</div></div>;
}
export function TrendChart({data,metric='requests',onSelect}:{data:DailyCount[];metric?:'requests'|'backlog';onSelect?:()=>void}){
 const vals=data.filter(x=>Number.isFinite(x.received)&&Number.isFinite(x.completed)&&Number.isFinite(x.open));
 if(!vals.length)return <EmptyChart onSelect={onSelect} message="날짜별 접수·완료·미완료 추이 집계가 필요합니다."/>;
 const width=600,height=200,left=34,right=12,top=18,bottom=32;
 const h=height-top-bottom, w=width-left-right;
 const yValues=vals.flatMap(x=>metric==='backlog'?[x.open]:[x.received,x.completed]);
 const max=Math.max(1,...yValues),xpos=(i:number)=>left+(vals.length<2?w/2:(i/(vals.length-1))*w), ypos=(v:number)=>top+(1-v/max)*h;
 const path=(key:'received'|'completed'|'open')=>vals.map((v,i)=>(i===0?'M':'L')+xpos(i).toFixed(1)+','+ypos(v[key]).toFixed(1)).join(' ');
 const freq=Math.max(1,Math.floor(vals.length/5));
 return <div className="da-line-wrap"><svg viewBox={'0 0 '+width+' '+height} role="img" aria-label="날짜별 접수·완료 또는 미완료 추이" className="da-line-chart">{[0,0.25,0.5,0.75,1].map(t=><g key={t}><line x1={left} x2={width-right} y1={top+h*(1-t)} y2={top+h*(1-t)} stroke="#E9EEF4" strokeDasharray="3 4"/><text x={left-7} y={top+h*(1-t)+4} textAnchor="end" fontSize="10" fill="#8A97A8">{Math.round(max*t)}</text></g>)}
 {metric==='backlog'?<path d={path('open')} stroke="#DA6C7A" fill="none" strokeWidth="3" strokeLinecap="round"/>:<><path d={path('received')} stroke="#246ECA" fill="none" strokeWidth="3" strokeLinecap="round"/><path d={path('completed')} stroke="#37A89B" fill="none" strokeWidth="3" strokeLinecap="round"/></>}
 {vals.map((v,i)=>i%freq===0||i===vals.length-1?<text key={i} x={xpos(i)} y={height-8} fontSize="10" textAnchor="middle" fill="#8492A3">{v.date.slice(5)}</text>:null)}</svg><div className="da-chart-legend"><span><i style={{background:metric==='backlog'?'#DA6C7A':'#246ECA'}}/>{metric==='backlog'?'미완료 잔량':'접수'}</span>{metric!=='backlog'&&<span><i style={{background:'#37A89B'}}/> 완료</span>}</div></div>;
}
export function FunnelChart({items,onSelect}:{items:StageCount[];onSelect?:(x:string)=>void}){
 if(!items.length)return <EmptyChart onSelect={onSelect?()=>onSelect(''):undefined} kind="funnel" message="현재 분포와 별도인 단계 도달 누적 집계가 필요합니다."/>;
 const max=Math.max(1,...items.map(x=>x.count));
 return <div className="da-funnel">{items.map((x,i)=><button className="da-funnel-row" key={x.stage} onClick={()=>onSelect?.(x.stage)}><span className="da-funnel-label">{x.label}</span><span className="da-funnel-base"><span style={{width:(Math.max(0,x.count)/max*100)+'%',background:colors[i%colors.length]}}/></span><b>{fmt(x.count)}건</b></button>)}<p className="da-chart-footnote">단계별 개수는 한 시점의 상태별 건수인지, 각 단계 도달 누적인지 데이터 계약에 반드시 명시해야 합니다.</p></div>;
}
export function GanttChart({items,onSelect}:{items:TimelineWork[];onSelect?:(id:string)=>void}){
 const clean=items.filter(x=>!Number.isNaN(Date.parse(x.startAt))&&!Number.isNaN(Date.parse(x.dueAt))&&Date.parse(x.dueAt)>=Date.parse(x.startAt));
 if(!clean.length)return <EmptyChart onSelect={onSelect?()=>onSelect(''):undefined} kind="gantt" message="확정된 계획 시작일·기한이 있는 작업만 표시합니다."/>;
 const first=Math.min(...clean.map(x=>Date.parse(x.startAt))),last=Math.max(...clean.map(x=>Date.parse(x.dueAt)));
 const span=Math.max(24*3600*1000,last-first);
 return <div className="da-gantt"><div className="da-gantt-dates"><span>{new Date(first).toLocaleDateString('ko-KR')}</span><span>{new Date(last).toLocaleDateString('ko-KR')}</span></div>{clean.slice(0,12).map(x=>{const start=(Date.parse(x.startAt)-first)/span*100,len=Math.max(1,(Date.parse(x.dueAt)-Date.parse(x.startAt))/span*100);return <button key={x.id} className="da-gantt-row" onClick={()=>onSelect?.(x.id)} title={x.label+' | '+x.startAt+' ~ '+x.dueAt}><span className="da-gantt-label" title={x.label}>{x.label}</span><span className="da-gantt-track"><span style={{left:start+'%',width:Math.min(len,100-start)+'%',background:x.doneAt?'#37A89B':'#246ECA'}}/></span><small>{x.operator}</small></button>})}<div className="da-chart-footnote">녹색=완료일 있음 · 파란색=진행/계획 · 종료일을 자동 추정하지 않습니다.</div></div>;
}
export function HeatMap({items,onSelect}:{items:HeatCell[];onSelect?:(operatorId:string,stage:string)=>void}){
 if(!items.length)return <EmptyChart onSelect={onSelect?()=>onSelect('',''):undefined} kind="heatmap" message="운영자 × 업무 단계별 실제 집계가 필요합니다."/>;
 const stages=Array.from(new Map(items.map(x=>[x.stage,x.label])).entries()),ops=Array.from(new Map(items.map(x=>[x.operatorId,x.operatorName])).entries());
 const max=Math.max(1,...items.map(x=>x.count));
 return <div className="da-heatmap-overflow"><table className="da-heatmap"><thead><tr><th>운영자</th>{stages.map(([id,label])=><th key={id}>{label}</th>)}</tr></thead><tbody>{ops.map(([id,name])=><tr key={id}><th>{name}</th>{stages.map(([stage])=>{const value=items.find(x=>x.operatorId===id&&x.stage===stage)?.count??0;return <td key={stage}><button onClick={()=>onSelect?.(id,stage)} style={{background:`rgba(36,110,202,${.08+(value/max)*.84})`,color:value/max>.65?'white':'#254B77'}} title={name+' · '+stage+' '+value+'건'}>{fmt(value)}</button></td>})}</tr>)}</tbody></table></div>;
}
export function Sparkline({points,label,color='#246ECA',onSelect}:{points:HealthMetric[];label:string;color?:string;onSelect?:()=>void}){
 const v=points.filter(p=>Number.isFinite(p.value));if(v.length<2)return <EmptyChart onSelect={onSelect} kind="resource" message="자원 시계열 미측정"/>;
 const hi=Math.max(1,...v.map(x=>x.value)),low=Math.min(0,...v.map(x=>x.value)),span=Math.max(1,hi-low),w=130,h=35;
 const path=v.map((x,i)=>(i?'L':'M')+(i/(v.length-1)*w).toFixed(1)+','+(h-(x.value-low)/span*h).toFixed(1)).join(' ');
 return <svg className="da-sparkline" viewBox={'0 0 '+w+' '+h} role="img" aria-label={label}><path d={path} stroke={color} fill="none" strokeWidth="2.5"/></svg>;
}
