import type { DashboardSnapshot } from '../types'
export function MethodologyDrawer({data,onClose}:{data:DashboardSnapshot;onClose:()=>void}){
  return <div className="backdrop" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><aside className="drawer" role="dialog" aria-modal="true" aria-label="Methodology">
    <button className="close" onClick={onClose}>Close ×</button><p className="eyebrow">TRANSPARENT BY DESIGN</p><h2>How impact is calculated</h2><p>{data.methodology.summary}</p>
    <div className="weight-grid">{Object.entries(data.methodology.weights).map(([k,v])=><div key={k}><b>{v}%</b><span>{k}</span></div>)}</div>
    <h3>Two-stage method</h3><ol><li>GPT-5.5 scores change significance, blast radius, logic, architecture, cross-component reach, change scope, and PR value.</li><li>Deterministic code calculates component importance, meaningful-output percentile, ownership frequency/continuity/share, and the final ranking. The model never chooses the ranking.</li></ol>
    <h3>Guardrails</h3><p>Bots, self-reviews, empty approvals, and shallow review comments are excluded. Diff size is context, never an impact metric.</p>
    <h3>Limitations</h3><ul>{data.methodology.limitations.map(x=><li key={x}>{x}</li>)}</ul>
  </aside></div>
}
