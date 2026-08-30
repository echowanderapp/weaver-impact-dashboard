import { useEffect, useState } from 'react'
import type { DashboardSnapshot, Engineer } from './types'
import { RankCard } from './components/RankCard'
import { EngineerDetail } from './components/EngineerDetail'
import { MethodologyDrawer } from './components/MethodologyDrawer'

export default function App(){
  const [data,setData]=useState<DashboardSnapshot|null>(null),[selected,setSelected]=useState<Engineer|null>(null),[error,setError]=useState(''),[method,setMethod]=useState(false)
  useEffect(()=>{fetch(`${import.meta.env.VITE_API_BASE_URL||''}/api/dashboard`).then(r=>{if(!r.ok)throw Error(`API returned ${r.status}`);return r.json()}).then((d:DashboardSnapshot)=>{setData(d);setSelected(d.engineers[0]||null)}).catch(e=>setError(e.message))},[])
  useEffect(()=>{const close=(e:KeyboardEvent)=>e.key==='Escape'&&setMethod(false);addEventListener('keydown',close);return()=>removeEventListener('keydown',close)},[])
  if(error)return <main className="state"><p className="eyebrow">CONNECTION ERROR</p><h1>Impact data is unavailable.</h1><p>{error}. Confirm the backend URL and try again.</p></main>
  if(!data)return <main className="state"><div className="pulse"/><p>Loading impact evidence…</p></main>
  if(!selected)return <main className="state"><h1>No eligible engineers found.</h1><p>Regenerate the snapshot with a complete 90-day window.</p></main>
  const preview=data.engineers.some(x=>x.login.startsWith('preview-'))
  return <><main><header className="topbar"><div><p className="eyebrow">ENGINEERING INTELLIGENCE / {data.repository}</p><h1>Who moved PostHog forward?</h1><p>Evidence-backed impact across {data.window_start} — {data.window_end}</p></div><button className="method-button" onClick={()=>setMethod(true)}>How this works <span>↗</span></button></header>
    {preview&&<div className="preview-banner">Preview data — add GitHub and OpenAI credentials, then run ingestion before submission.</div>}
    <section className="workspace"><aside className="ranking"><div className="section-title"><span>TOP CONTRIBUTORS</span><small>Impact, not activity</small></div>{data.engineers.map(x=><RankCard key={x.login} engineer={x} selected={x.login===selected.login} onSelect={()=>setSelected(x)}/>)}</aside><EngineerDetail engineer={selected}/></section>
    <footer><span>Generated {new Date(data.generated_at).toLocaleString()}</span><span>Model: {data.model} · Snapshot-powered</span></footer>
  </main>{method&&<MethodologyDrawer data={data} onClose={()=>setMethod(false)}/>}</>
}
