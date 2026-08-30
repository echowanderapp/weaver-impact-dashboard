import type { Engineer } from '../types'
import { ImpactChart } from './ImpactChart'
export function EngineerDetail({engineer}:{engineer:Engineer}){
  return <section className="detail">
    <header className="detail-head"><div><p className="eyebrow">#{engineer.rank} IMPACT PROFILE</p><h2>{engineer.name||engineer.login}</h2><p>{engineer.summary}</p></div><div className="hero-score">{engineer.score}<small>impact score</small></div></header>
    <div className="detail-grid"><div><h3>Impact signature</h3><ImpactChart scores={engineer.dimensions}/><p className="context">Main area: {engineer.primary_component||'unclassified'} · {engineer.active_weeks}/13 active weeks · {engineer.component_share}% component share · {engineer.meaningful_output} meaningful output</p></div>
    <div><h3>Evidence behind the score</h3><div className="evidence-list">{engineer.evidence.map(item=><a href={item.url} target="_blank" rel="noreferrer" key={item.url} className="evidence"><span>{item.kind==='review'?'REVIEW':'SHIPPED'} · {item.impact_score}</span><strong>{item.title}</strong><p>{item.explanation}</p><i>View on GitHub ↗</i></a>)}</div></div></div>
  </section>
}
