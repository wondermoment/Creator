"""Customer-readable reports and evidence-based readiness; no synthetic results."""
from html import escape
from fastapi import Request
from fastapi.responses import HTMLResponse


def saved_expert_generations(content, jobs):
    """Count only successful expert answers actually saved in this tenant."""
    linked = {x.get('repurpose_job_id') for x in content if not x.get('generation_error')}
    return {j['id'] for j in jobs if j.get('id') in linked
            and j.get('job_type') == 'expert_chat' and j.get('status') == 'succeeded'
            and j.get('payload', {}).get('workflow', 'chat') in ('chat', 'repurpose')
            and not j.get('result', {}).get('discarded')
            and j.get('result', {}).get('answer') and j.get('result', {}).get('model')}


def readiness(S, c, pid):
    items = S['items']
    knowledge, content, pubs, jobs, channels = [items(c, pid, k) for k in ('knowledge', 'content', 'publication', 'execution', 'connector')]
    verified = {x['provider'] for x in channels if x.get('status') == 'verified'}
    return [
        {'name': '企业事实已核准', 'ok': any(S['knowledge_usable'](c, pid, x) for x in knowledge), 'page': 'knowledge', 'detail': '至少一份当前来源版本有效的确认资料'},
        {'name': '真实模型已验证', 'ok': 'model' in verified, 'page': 'skills', 'detail': '连接测试成功；内容质量仍需审核'},
        {'name': '已产出真实模型草稿', 'ok': any(x.get('model_run') and not x.get('generation_error') for x in content) or bool(saved_expert_generations(content, jobs)), 'page': 'content', 'detail': '执行成功并保留模型与知识快照'},
        {'name': '当前版本完成客户审核', 'ok': any(S['content_approval_summary'](c, pid, x)['effective_approved'] for x in content), 'page': 'content', 'detail': '当前版本审批及引用知识有效，且已选择渠道；不代表外部渠道已接通'},
        {'name': '取得公开发布回执', 'ok': any(x['status'] in ('published', 'recorded') and x.get('url') for x in pubs), 'page': 'publish', 'detail': '区分平台确认与人工登记，草稿不计入'},
        {'name': '实际咨询已进入跟进', 'ok': any(x['status'] in ('contacted', 'qualified', 'won') for x in items(c, pid, 'lead')), 'page': 'leads', 'detail': '依据成员跟进记录，非浏览量推算'},
        {'name': '执行异常已处理', 'ok': not any(x['status'] in ('failed', 'unknown') for x in jobs) and not any(p.get('requires_attention') for p in pubs), 'page': 'delivery', 'detail': '没有未处理的失败、结果未知或旧版远端记录；不等于全部服务已接通'}
    ]


def register(S):
    app = S['app']

    @app.get('/api/projects/{pid}/readiness')
    def get_readiness(pid: str, request: Request):
        with S['db']() as c:
            S['scope'](c, request, pid)
            checks = readiness(S, c, pid)
            return {'checks': checks, 'completed': sum(x['ok'] for x in checks), 'total': len(checks), 'meaning': '当前企业交付链状态，不是 GEO 评分或生产安全认证'}

    @app.get('/api/projects/{pid}/report')
    def report(pid: str, request: Request):
        with S['db']() as c:
            S['scope'](c, request, pid)
            project = S['project'](c, pid)
            records = {k: S['items'](c, pid, k) for k in ('content', 'publication', 'knowledge', 'lead', 'execution', 'observation', 'geo_snapshot', 'seo_audit', 'diagnosis', 'media_opportunity')}
            for doc in records['knowledge']:
                doc['review_summary'] = S['knowledge_review_summary'](c, pid, doc)
            for doc in records['content']:
                doc['approval_summary'] = S['content_approval_summary'](c, pid, doc)
            checks = readiness(S, c, pid)
            stats = S['stats'](c, pid)
        esc = lambda x: escape(str(x if x is not None else ''), quote=True)
        publications = records['publication']
        valid_knowledge = sum(k['review_summary']['effective_confirmed'] for k in records['knowledge'])
        approval_notes = ''.join('<li>'+esc(k['title'])+' · 当前 v'+esc(k['revision'])
                                +' · 历史审批 v'+esc(k.get('approved_revision'))+'<small>'
                                +esc('；'.join(k['approval_summary']['reasons']))+'</small></li>'
                                for k in records['content'] if k['status']=='approved' and not k['approval_summary']['effective_approved'])
        knowledge_notes = ''.join(
            '<details><summary>'+esc(k['title'])+' · 当前 v'+esc(k['version'])+' · '
            +('当前有效' if k['review_summary']['effective_confirmed'] else '待核准 / 来源待核对')+'</summary>'
            +(''.join('<p><strong>'+esc(h['label'])+' · v'+esc(h['version'])+'</strong><small>'
                      +esc(h['actor'] or '审核人未记录')+' · '+esc(h['confirmed_at'] or '时间未记录')
                      +'</small><small style="overflow-wrap:anywhere">正文 SHA-256：'+esc(h['body_sha256'] or '未记录')+'</small></p>'
                      for h in reversed(k['review_summary']['history']))
              or '<p class="muted">未留存确认记录；不补写历史审核人或时间。</p>')+'</details>'
            for k in records['knowledge'])
        attention = [p for p in publications if p.get('requires_attention')]
        remote_notes = ''.join('<li><strong>旧版远端记录待处理 · '+esc(p['title'])+' · v'+esc(p['revision'])+'</strong><small>'
                              +esc(p.get('attention_reason',''))+'</small><p>核对状态：'
                              +esc({'draft':'远端草稿','publish':'远端已公开'}.get(p.get('remote_evidence',{}).get('platform_status'),'未知'))
                              +' · '+esc(p.get('remote_evidence',{}).get('observed_at',''))+'</p>'
                              +('<a href="'+esc(p['remote_evidence']['url'])+'" rel="noopener noreferrer">查看旧版远端证据</a>'
                                if p.get('remote_evidence',{}).get('url') else '远端未返回链接')+'</li>' for p in attention)
        disposition_labels = {'retained':'登记保留旧文','updated':'登记已更新','removed':'登记已撤下','reopen':'重新打开待处理'}
        disposition_notes = ''.join('<details><summary>旧版处理记录 · '+esc(p['title'])+'</summary>'
                                   +''.join('<p><strong>'+esc(disposition_labels.get(h['outcome'],h['outcome']))+'</strong> · 人工登记，未验证远端变更'
                                            +'<small>'+esc(h['actor'])+' · '+esc(h['recorded_at'])+'</small>'+esc(h['note'])
                                            +('<br><a href="'+esc(h['evidence_url'])+'" rel="noopener noreferrer">处理依据</a>' if h.get('evidence_url') else '')+'</p>'
                                            for h in p.get('disposition_history',[]))+'</details>'
                                   for p in publications if p.get('disposition_history'))
        samples = [s for d in records['diagnosis'] if d.get('status') != 'sample' for s in d.get('samples', [])]
        rows = ''.join('<tr><td>' + esc(p['title']) + '<small>v' + esc(p['revision']) + '</small></td><td>' + esc(p['channel']) + '</td><td>' + esc({'recorded': '人工登记回执', 'published': '平台确认发布', 'wp_draft': '官网草稿', 'cancelled': '旧版已撤销', 'awaiting_connector': '待交付'}.get(p['status'], p['status'])) + '</td><td>' + ('<a href="' + esc(p['url']) + '" rel="noopener noreferrer">查看交付链接</a>' if p.get('url') else '无公开回执') + '</td></tr>' for p in publications)
        evidence = ''.join('<details><summary>' + esc(s['platform']) + ' · ' + esc(s['question']) + '</summary><p class="muted">人工观察 · ' + esc(s['observed_at']) + '</p><pre>' + esc(s['answer']) + '</pre>' + ('<a href="' + esc(s['citation']) + '">引用页面</a>' if s.get('citation') else '<p>未记录引用 URL</p>') + '</details>' for s in samples)
        failures = [j for j in records['execution'] if j['status'] in ('failed', 'unknown')]
        generation_jobs = [j for j in records['execution'] if j['job_type'] == 'generate']
        discarded_jobs = [j for j in generation_jobs if j.get('result', {}).get('discarded')]
        saved_generations = sum(j['status'] == 'succeeded' and bool(j.get('result', {}).get('content_id'))
                                and not j.get('result', {}).get('discarded') for j in generation_jobs)
        saved_generations += len(saved_expert_generations(records['content'], records['execution']))
        discarded_notes = ''
        for job in discarded_jobs:
            result = job['result']
            usage = result.get('usage') or {}
            cost = result.get('estimated_cost')
            cost_text = (str(result.get('currency', '')) + ' ' + format(cost, '.6f')) if type(cost) in (int, float) else '费用未取得或未配置单价'
            discarded_notes += ('<details><summary>结果已舍弃 · '+esc(job['id'])+'</summary>'
                                +'<p>本次未产出可用稿件 · '+esc(result.get('reason') or '未覆盖当前内容')+'</p>'
                                +'<small>'+esc(job.get('finished_at') or job['created'])+'</small><p>'
                                +esc(usage.get('prompt_tokens', '—'))+' 输入 / '+esc(usage.get('completion_tokens', '—'))+' 输出 · '
                                +esc(cost_text)+'</p></details>')
        api_runs = records['observation']
        summary = {'草稿与内容': len(records['content']), '当前审核通过': stats['approved'], '平台确认发布': sum(p['status'] == 'published' for p in publications),
                   '人工登记回执': sum(p['status'] == 'recorded' for p in publications), '客资总数': stats['leads'], '已标记有效询盘': stats['qualified']}
        content = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(project['name'])} · 交付复盘报告</title><style>
        *{{box-sizing:border-box}}body{{font:15px/1.7 system-ui,"Microsoft YaHei",sans-serif;color:#202124;background:#f4f6f8;margin:0}}main{{max-width:1060px;margin:40px auto;padding:44px;background:#fff;border-top:5px solid #4285f4}}h1{{font-size:30px;margin:12px 0}}h2{{font-size:20px;border-top:1px solid #dadce0;padding-top:24px;margin-top:32px}}.muted,small{{color:#657184}}small{{display:block}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.metric{{border:1px solid #dadce0;padding:16px}}.metric b{{font-size:30px;display:block}}table{{width:100%;border-collapse:collapse}}td,th{{text-align:left;border-bottom:1px solid #dadce0;padding:12px}}a{{color:#1a73e8}}pre{{white-space:pre-wrap;font:inherit;background:#f6f8fa;padding:16px}}details{{border-bottom:1px solid #dadce0;padding:14px 0}}.note{{padding:16px;background:#e8f0fe}}.demo{{padding:16px;background:#fef7e0}}li{{margin:8px 0}}@media print{{body{{background:white}}main{{margin:0;max-width:none;padding:15px}}details{{break-inside:avoid}}}}@media(max-width:700px){{main{{margin:0;padding:22px}}.metrics{{grid-template-columns:repeat(2,1fr)}}}}
        </style></head><body><main><span class="muted">品牌铸匠 GEO / DELIVERY REVIEW</span><h1>{esc(project['name'])} · 企业交付复盘</h1><p class="muted">官网：{esc(project['website'])} · 导出时间：{esc(S['now']())}<br>范围：当前企业累计记录；不是月度增幅或效果归因报告。</p>
        {'<p class="demo">演示空间：含虚构样本，不作为真实客户效果证明。</p>' if project['demo'] else ''}
        <div class="metrics">{''.join('<div class="metric">'+esc(k)+'<b>'+esc(v)+'</b></div>' for k,v in summary.items())}</div>
        <h2>01 / 交付链进度</h2><ul>{''.join('<li>'+('已具备' if x['ok'] else '待完成')+' · '+esc(x['name'])+'<small>'+esc(x['detail'])+'</small></li>' for x in checks)}</ul>
        <h2>02 / 发布交付明细</h2><table><thead><tr><th>成果与版本</th><th>渠道</th><th>回执口径</th><th>证据</th></tr></thead><tbody>{rows or '<tr><td colspan="4">暂无发布交付记录。</td></tr>'}</tbody></table>
        {disposition_notes}
        <h2>03 / GEO 观察与证据</h2><div class="note">人工观察 {len(samples)} 条；模型 API 观测 {len(api_runs)} 条；外部监测汇总 {len(records['geo_snapshot'])} 份。三类口径分别记录，不合并计算全平台可见度。</div>
        <p>当前人工样本中记录品牌提及 {sum(bool(s.get('mentioned')) for s in samples)} 次。结果受问题、时间、语言、账号与采集方式影响，不能据此推断全网排名。</p>{evidence or '<p class="muted">尚无可展示的真实人工回答证据。</p>'}
        {''.join('<details><summary>模型 API · '+esc(o['question'])+'</summary><p class="muted">'+esc(o['model'])+' · '+esc(o['observed_at'])+' · '+esc(o.get('web_search','未确认联网'))+'</p><pre>'+esc(o['answer'])+'</pre></details>' for o in api_runs)}
        <h2>04 / 知识与网站</h2><p>当前有效确认资料 {valid_knowledge} 份；待核准或来源待核对资料 {len(records['knowledge'])-valid_knowledge} 份；单页网站检查 {len(records['seo_audit'])} 份；知识已过期内容 {sum(k['approval_summary']['sources_outdated'] for k in records['content'])} 篇。</p>
        <p class="muted">当前审核通过数校验审批版本、引用知识有效性及所选渠道；历史审批保留，但失效记录不计入。不代表外部渠道已接通或文章已发布。</p>{'<h3>历史审批待复核</h3><ul>'+approval_notes+'</ul>' if approval_notes else ''}
        <h3>知识确认记录</h3><p class="muted">历史确认不代表当前资料仍有效。正文校验值用于版本追溯，不是第三方事实认证；时间按记录中的时区显示。</p>{knowledge_notes or '<p class="muted">暂无知识资料。</p>'}
        <h2>05 / 客资跟进</h2><p>跟进中 {sum(l['status']=='contacted' for l in records['lead'])} 条，有效询盘 {sum(l['status']=='qualified' for l in records['lead'])} 条，成员记录成交 {sum(l['status']=='won' for l in records['lead'])} 条。</p><p class="muted">不在客户报告中公开个人联系方式；有效性及成交由成员回填，不是自动归因于 GEO。</p>
        <h2>06 / 待处理与下一步</h2><ul>{(''.join('<li>'+esc(j['job_type'])+' · '+esc(j['stage'])+'<small>'+esc(j['error'])+'</small></li>' for j in failures)+remote_notes) or '<li>当前无未处理的执行异常。</li>'}{''.join('<li>'+esc(x['name'])+'：'+esc(x['detail'])+'</li>' for x in checks if not x['ok'])}</ul>
        <h3>模型生成结果与用量</h3><p>已保存生成结果 {saved_generations} 次；结果已舍弃 {len(discarded_jobs)} 次。</p><p class="muted">已保存包括文章生成及已落为稿件的专家对话、一鱼多吃，按任务去重；未保存的对话、参考拆解、连接测试或GEO观测不计入。舍弃数为文章生成任务的历史记录。已保存不等于当前仍有效、已审核或已发布。舍弃结果不会退回已经发生的调用用量；费用为配置单价估算，非供应商账单。缺失用量与价格保留未知；重新创作需另行发起。</p>{discarded_notes}
        <p class="muted">所有数字来自当前企业记录。发布量、AI 提及、网站访问、咨询与成交分别统计；尚未取得的数据保留未知。可使用浏览器打印保存为 PDF。</p></main></body></html>'''
        return HTMLResponse(content)
