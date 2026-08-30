from collections import defaultdict
from datetime import datetime

WEIGHTS = {"impact": .40, "complexity": .25, "output": .20, "ownership": .15}
DIMS = tuple(WEIGHTS)

COMPONENT_RULES = (
    (10, "ingestion", ("capture/", "ingestion", "kafka", "auth", "posthog/auth")),
    (9, "feature_flags", ("feature_flag", "feature-flags", "flags/", "critical")),
    (8, "session_replay", ("session_replay", "session-replay", "recordings", "api/")),
    (6, "product_shared", ("products/", "posthog/", "frontend/src/lib", "frontend/src/scenes")),
    (4, "tooling", ("frontend/", "scripts/", "bin/", "tools/")),
    (2, "docs", ("docs/", ".md", "readme")),
)


def classify_component(pr: dict) -> tuple[str, float]:
    paths = [node.get("path", "").lower() for node in pr.get("files", {}).get("nodes", [])]
    matches = [(importance, name) for importance, name, patterns in COMPONENT_RULES if any(any(pattern in path for pattern in patterns) for path in paths)]
    return max(matches, default=(4, "unclassified"))


def percentile(value: float, population: list[float]) -> float:
    if len(population) <= 1:
        return 5.0
    below = sum(item < value for item in population)
    equal = sum(item == value for item in population)
    return round(((below + .5 * equal) / len(population)) * 10, 2)


def is_substantive_review(review: dict) -> bool:
    return review.get("state") == "CHANGES_REQUESTED" or len((review.get("body") or "").strip()) >= 80


def rank_engineers(prs: list[dict], classifications: dict) -> list[dict]:
    people: dict[str, dict] = defaultdict(lambda: {"prs":[],"reviews":[],"confidence":[],"components":defaultdict(lambda:{"value":0.0,"count":0,"weeks":set()})})
    component_totals: dict[str, float] = defaultdict(float)
    for pr in prs:
        author = pr["author"]
        login = author["login"]
        classification = classifications[pr["number"]]
        record = classification.model_dump() if hasattr(classification, "model_dump") else classification
        component_importance, component = classify_component(pr)
        impact = .5 * component_importance + .3 * record["change_significance"] + .2 * record["blast_radius"]
        complexity = .35 * record["logic"] + .30 * record["architecture"] + .20 * record["cross_component"] + .15 * record["change_scope"]
        pr_value = record["pr_value"] * record["confidence"]
        week = datetime.fromisoformat(pr["mergedAt"].replace("Z", "+00:00")).strftime("%G-W%V")
        people[login].update({"login":login,"name":None,"avatar_url":author["avatarUrl"],"profile_url":author["url"]})
        people[login]["prs"].append({"title":pr["title"],"url":pr["url"],"kind":"pull_request","explanation":f"{component}: {record['explanation']}","impact_score":round(impact*10,1),"impact":impact,"complexity":complexity,"value":pr_value,"component":component})
        people[login]["confidence"].append(record["confidence"])
        area = people[login]["components"][component]
        area["value"] += pr_value
        area["count"] += 1
        area["weeks"].add(week)
        area["importance"] = component_importance
        component_totals[component] += pr_value
        for review in pr.get("reviews", {}).get("nodes", []):
            reviewer = review.get("author") or {}
            if reviewer.get("login") and reviewer["login"] != login and is_substantive_review(review):
                rlogin = reviewer["login"]
                people[rlogin].update({"login":rlogin,"name":None,"avatar_url":reviewer["avatarUrl"],"profile_url":reviewer["url"]})
                people[rlogin]["reviews"].append({"title":f"Review: {pr['title']}","url":review.get("url") or pr["url"],"kind":"review","explanation":"Substantive review that helped shape a shipped change.","impact_score":round(impact*.25,1)})
    output_raw = [sum(pr["value"] for pr in person["prs"]) for person in people.values()]
    frequency_population = [area["value"] for person in people.values() for area in person["components"].values()]
    ranked = []
    for person in people.values():
        authored_value = sum(pr["value"] for pr in person["prs"])
        if not person["prs"]:
            continue
        impact = sum(pr["impact"]*pr["value"] for pr in person["prs"]) / authored_value if authored_value else 0
        complexity = sum(pr["complexity"]*pr["value"] for pr in person["prs"]) / authored_value if authored_value else 0
        output = percentile(authored_value, output_raw)
        ownership_candidates = []
        for component, area in person["components"].items():
            frequency = percentile(area["value"], frequency_population)
            continuity = min(len(area["weeks"]) / 13 * 10, 10)
            component_share = area["value"] / component_totals[component] * 10 if component_totals[component] else 0
            ownership_score = (.4*frequency + .3*continuity + .3*component_share) * area["importance"] / 10
            ownership_candidates.append((ownership_score, component, len(area["weeks"]), component_share, area["count"]))
        ownership, main_component, active_weeks, component_share, component_prs = max(ownership_candidates, default=(0,"unclassified",0,0,0))
        dimensions = {"impact":round(impact,1),"complexity":round(complexity,1),"output":round(output,1),"ownership":round(ownership,1)}
        score = round(sum(dimensions[d]*WEIGHTS[d] for d in DIMS)*10,1)
        strongest = max(DIMS,key=lambda d: dimensions[d])
        evidence = sorted(person["prs"],key=lambda x:x["impact_score"],reverse=True)[:3]
        if len(evidence)<3:
            evidence += sorted(person["reviews"],key=lambda x:x["impact_score"],reverse=True)[:3-len(evidence)]
        if not evidence:
            continue
        ranked.append({**{k:person[k] for k in ("login","name","avatar_url","profile_url")},"score":score,"strongest_dimension":strongest,"dimensions":dimensions,"confidence":round(sum(person["confidence"])/len(person["confidence"]),2) if person["confidence"] else .4,"summary":f"{component_prs} meaningful changes in {main_component}; active {active_weeks}/13 weeks with {component_share*10:.0f}% of the component's visible output.","authored_prs":len(person["prs"]),"substantive_reviews":len(person["reviews"]),"primary_component":main_component,"active_weeks":active_weeks,"component_share":round(component_share*10,1),"meaningful_output":round(authored_value,1),"evidence":[{k:v for k,v in item.items() if k in ("title","url","kind","explanation","impact_score")} for item in evidence]})
    ranked.sort(key=lambda p:(-p["score"],-p["dimensions"]["impact"],p["login"]))
    for index,person in enumerate(ranked[:5],1): person["rank"] = index
    return ranked[:5]
