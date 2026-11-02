import {useId,useRef,useState} from 'react';
import './file-selection.css';

type Props={label:string;accept:string;files:File[];disabled?:boolean;maxFiles?:number;hint?:string;onFiles:(files:File[])=>void;onRemove:(index:number)=>void};
export function FileSelection({label,accept,files,disabled=false,maxFiles=10,hint,onFiles,onRemove}:Props){
 const input=useRef<HTMLInputElement>(null),description=useId(),[drag,setDrag]=useState(false);
 return <section className={'portal-file-selection'+(drag?' is-dragging':'')} aria-label={label+' 영역'}
  onDragOver={e=>{e.preventDefault();if(!disabled)setDrag(true);}} onDragLeave={()=>setDrag(false)}
  onDrop={e=>{e.preventDefault();setDrag(false);if(!disabled)onFiles(Array.from(e.dataTransfer.files));}}>
  <div className="portal-file-heading"><strong>{label}</strong><button type="button" disabled={disabled} onClick={()=>input.current?.click()}>파일 선택</button></div>
  <input ref={input} className="portal-file-input" type="file" tabIndex={-1} multiple={maxFiles>1} accept={accept} disabled={disabled} aria-label={label} aria-describedby={description} onChange={e=>{onFiles(Array.from(e.target.files??[]));e.currentTarget.value='';}}/>
  <p id={description}>{hint??'파일 선택 또는 끌어놓기'} · 최대 {maxFiles}개 · 파일당 20MB 이하</p>
  {files.length?<><p role="status">선택한 파일 {files.length}개 · 분석·저장은 아래 업무 버튼에서 진행합니다.</p><ul>{files.map((file,i)=><li key={i}><span>{file.name}</span><button type="button" disabled={disabled} aria-label={file.name+' 선택 취소'} onClick={()=>onRemove(i)}>선택 취소</button></li>)}</ul></>:<p>새로 선택한 파일이 없습니다.</p>}
 </section>;
}
