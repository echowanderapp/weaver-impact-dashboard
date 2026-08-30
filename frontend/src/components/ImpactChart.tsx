import type { DimensionScores } from '../types'
const labels={impact:'Impact',complexity:'Complexity',output:'Meaningful output',ownership:'Ownership'}
export function ImpactChart({scores}:{scores:DimensionScores}){
  return <div className="impact-chart">{Object.entries(scores).map(([key,value])=><div className="bar-row" key={key}>
    <div className="bar-label"><span>{labels[key as keyof DimensionScores]}</span><b>{value}</b></div>
    <div className="bar-track"><span style={{width:`${value*10}%`}} /></div>
  </div>)}</div>
}
