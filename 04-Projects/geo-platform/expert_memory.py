"""Bounded recall over durable, tenant-scoped expert conversations.

Caller supplies only this project's jobs. User requests are context, never
verified knowledge; assistant answers remain under the source-version gate.
"""
import re


def terms(text):
    words = set(re.findall(r'[a-z0-9]{2,}', text.lower()))
    for run in re.findall(r'[\u4e00-\u9fff]+', text):
        words.update(run[i:i+2] for i in range(len(run)-1))
    return words


def recall_requests(jobs, actor, question):
    rows = [j for j in jobs if j.get('job_type') == 'expert_chat'
            and j.get('payload', {}).get('workflow') not in ('reference_analysis','repurpose','geo_diagnosis')
            and j.get('actor') == actor and j.get('status') != 'cancelled'
            and j.get('payload', {}).get('question', '').strip()]
    query = terms(question)
    ranked = sorted(rows, key=lambda j: len(query & terms(j['payload']['question'])), reverse=True)
    related = [j for j in ranked if query & terms(j['payload']['question'])][:8]
    preferences = [j for j in rows if re.search(
        r'以后|始终|记住|不要|必须|统一|风格|受众|偏好|改为|改成|更正', j['payload']['question'])][:8]
    selected = {j['id'] for j in rows[:8] + related + preferences}
    # Chronological context lets explicit newer corrections win. Full original
    # turns stay in SQLite even when omitted from this bounded model request.
    return [{'job_id': j['id'], 'expert_id': j['payload'].get('expert_id'),
             'created': j.get('created', ''), 'request': j['payload']['question'][:1000]}
            for j in reversed(rows) if j['id'] in selected]
