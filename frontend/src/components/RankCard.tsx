import type { Engineer } from '../types'
export function RankCard({engineer,selected,onSelect}:{engineer:Engineer;selected:boolean;onSelect:()=>void}){
  return <button className={`rank-card ${selected?'selected':''}`} onClick={onSelect}>
    <span className="rank">{String(engineer.rank).padStart(2,'0')}</span>
    <img src={engineer.avatar_url} alt="" />
    <span className="rank-copy"><strong>{engineer.name||engineer.login}</strong><small>@{engineer.login}</small></span>
    <span className="score">{engineer.score}<small>/100</small></span>
  </button>
}
