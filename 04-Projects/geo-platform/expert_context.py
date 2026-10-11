"""Deterministic, verbatim paragraph selection for automatic expert retrieval.

Full sources stay in the execution snapshot for version checks. This projection
is for the model only; no generated summaries or partial sentences are used.
"""
import re
from expert_memory import terms

BODY_BUDGET = 12000


def paragraphs(body):
    result=[]
    start=0
    for boundary in re.finditer(r'\n[ \t\r]*\n',body):
        if body[start:boundary.start()].strip():result.append((start,boundary.start()))
        start=boundary.end()
    if body[start:].strip():result.append((start,len(body)))
    return result


def project_sources(sources, question, budget=BODY_BUDGET):
    original=sum(len(s['body']) for s in sources)
    if original<=budget:
        return [dict(s) for s in sources], {'mode':'full','original_chars':original,'sent_chars':original,'budget_chars':budget}
    query=terms(question)
    spans=[paragraphs(s['body']) for s in sources]
    ranked=[]
    for i,source in enumerate(sources):
        for j,(start,end) in enumerate(spans[i]):
            score=len(query & terms(source['body'][start:end]))
            if score:ranked.append((-score,i,j))
    selected=[set() for _ in sources]
    used=0
    for _,i,j in sorted(ranked):
        # Keep immediate neighbors intact; distant qualifications may still be omitted.
        window=set(range(max(0,j-1),min(len(spans[i]),j+2)))
        extra=window-selected[i]
        cost=sum(spans[i][n][1]-spans[i][n][0] for n in extra)
        if cost and used+cost<=budget:
            selected[i].update(extra);used+=cost
    projected=[]
    for i,source in enumerate(sources):
        excerpts=[]
        for j in sorted(selected[i]):
            start,end=spans[i][j]
            excerpts.append({'paragraph':j+1,'start':start,'end':end,'text':source['body'][start:end]})
        # Preserve list order and source ids so [n] retains its existing meaning.
        projected.append({**{k:v for k,v in source.items() if k!='body'},'body':'',
            'excerpts':excerpts,'partial':True,'original_chars':len(source['body']),
            'selection_note':'仅收到相关段落与相邻段落，不能推断全文；未覆盖事实请说明需补资料' if excerpts else '本次预算内无完整匹配段落，不得依据标题推断事实'})
    return projected,{'mode':'excerpts','original_chars':original,'sent_chars':used,
                      'budget_chars':budget,'selected_paragraphs':sum(map(len,selected)),
                      'omitted_sources':sum(not s for s in selected)}
