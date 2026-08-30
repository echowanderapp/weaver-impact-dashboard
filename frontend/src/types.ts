export type Dimension = 'impact' | 'complexity' | 'output' | 'ownership'
export type DimensionScores = Record<Dimension, number>
export interface Evidence { title:string; url:string; kind:'pull_request'|'review'; explanation:string; impact_score:number }
export interface Engineer { rank:number; login:string; name:string|null; avatar_url:string; profile_url:string; score:number; strongest_dimension:Dimension; dimensions:DimensionScores; confidence:number; summary:string; authored_prs:number; substantive_reviews:number; primary_component?:string; active_weeks:number; component_share:number; meaningful_output:number; evidence:Evidence[] }
export interface DashboardSnapshot { repository:string; window_start:string; window_end:string; generated_at:string; model:string; methodology:{weights:DimensionScores; summary:string; limitations:string[]}; engineers:Engineer[] }
