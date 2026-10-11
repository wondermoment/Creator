const fs=require('fs'),vm=require('vm'),assert=require('assert');
const ctx=vm.createContext({console,Intl,Date,URL,URLSearchParams,Map,Set,document:{querySelector(){return {addEventListener(){}}},addEventListener(){},hidden:false},window:{addEventListener(){}},location:{hash:'#skills?expert=strategist'},localStorage:{getItem(){return null}},setInterval(){},setTimeout(){},clearTimeout(){},fetch(){throw Error('No network expected')}});
for(const name of ['app','planning','knowledge','manager','leads','delivery','sample','experts'])vm.runInContext(fs.readFileSync(`static/${name}.js`,'utf8'),ctx);
function render(text){ctx.input=text;return vm.runInContext('expertMarkdown(input)',ctx)}
const answer='# 审核清单\n\n1. **事实来源**：核对[1]和版本。\n2. **客户问题**：明确对象。\n\n## 下一步\n- 核准事实\n- 再提交审核';
let html=render(answer);assert(html.includes('<h3>审核清单</h3>'));assert(html.includes('<h4>下一步</h4>'));assert(html.includes('<strong>事实来源</strong>'));assert(html.includes('<li value="2">'));assert(html.includes('<ul>'));assert(html.includes('[1]'));assert(!html.includes('**'));
html=render('3. 从第三步开始\n   延续说明\n4. 第四步\n\n普通段落\n保留换行');assert(html.includes('<li value="3">从第三步开始<br>延续说明</li>'));assert(html.includes('<p>普通段落<br>保留换行</p>'));
html=render('> 仅供参考\n\n`**字面内容**`\n\n```html\n<img src=x onerror=alert(1)>\n**不要渲染**\n```');assert(html.includes('<blockquote>仅供参考</blockquote>'));assert(html.includes('<code>**字面内容**</code>'));assert(html.includes('&lt;img src=x onerror=alert(1)&gt;'));assert(!html.includes('<strong>不要渲染'));
for(const attack of ['<script>alert(1)</script>','**<img src=x onerror=alert(1)>**','[链接](javascript:alert(1))','![图](https://tracker.invalid/pixel)','&#60;svg onload=alert(1)&#62;','```"><svg onload=alert(1)>\n<script>bad</script>','</pre><iframe srcdoc="evil">','## <a href="javascript:alert(1)">点此</a>']){
 html=render(attack);assert(!/<(?:script|img|svg|iframe|a|style)\b/i.test(html),attack);if(attack.startsWith('&#60;'))assert(html.includes('&amp;#60;'));
 const tags=html.match(/<[^>]+>/g)||[];assert(tags.every(tag=>/^<\/?(?:p|br|strong|code|pre|blockquote|h[3-5]|ul|ol|li)(?: value="\d+")?>$/.test(tag)),tags.join(','));
}
assert.equal(render('未闭合 **加粗\n普通换行'),'<p>未闭合 **加粗<br>普通换行</p>');
assert(render('~~~~\n```\n原样\n~~~~').includes('<code>```\n原样</code>'));
assert.equal(render('```\n未闭合代码'),'<pre><code>未闭合代码</code></pre>');
vm.runInContext(`pid='p';activeExpert='strategist';state={role:'owner',execution:[{id:'j',job_type:'expert_chat',status:'succeeded',created:'2026-10-03',payload:{expert_id:'strategist',sources:[],soul_version:1,skill_version:1,skill_name:'策略',question:'给出清单'},result:{answer:input,model:'test',usage:{}}}]};`,ctx);
ctx.input=answer;vm.runInContext('state.execution[0].result.answer=input',ctx);const before=vm.runInContext('JSON.stringify(state)',ctx);
html=vm.runInContext('expertConversation()',ctx);assert(html.includes('class="expert-markdown"'));assert(html.includes('<strong>事实来源</strong>'));assert(html.includes('继续编辑图文'));assert.equal(vm.runInContext('JSON.stringify(state)',ctx),before);
vm.runInContext(`state.execution[0].result.discarded=true;state.execution[0].result.reason='引用已更新'`,ctx);html=vm.runInContext('expertConversation()',ctx);assert(!html.includes('class="expert-markdown"'));assert(html.includes('引用已更新'));
console.log('PASS: readable expert Markdown, safe HTML/link/image fallback, code fences, citations, unchanged saved answer and discarded-result gate');

vm.runInContext(`state.execution[0].payload.context_selection={mode:'excerpts',sent_chars:11900,original_chars:45080}`,ctx);
html=vm.runInContext('expertConversation()',ctx);assert(html.includes('11900 / 45080'));assert(html.includes('未传全文'));assert(html.includes('本次资料来源'));
vm.runInContext(`state.execution[0].payload.context_selection.sent_chars='<img src=x>'`,ctx);
html=vm.runInContext('expertConversation()',ctx);assert(!html.includes('<img'));assert(html.includes('&lt;img'));
vm.runInContext(`delete state.execution[0].payload.context_selection`,ctx);
assert(!vm.runInContext('expertConversation()',ctx).includes('未传全文'));
console.log('PASS: excerpt transparency, safe values, no misleading note on legacy jobs');
html=render('| 时间 | 口播 |\n|---|:---:|\n| 0–3秒 | **重点** [1] |\n| 3–10秒 | A\\|B |\n\n后续说明');
assert(html.includes('<table>'));assert(html.includes('<th scope="col">时间</th>'));assert(html.includes('<td><strong>重点</strong> [1]</td>'));assert(html.includes('<td>A|B</td>'));assert(html.endsWith('<p>后续说明</p>'));
html=render('| 时间 | 口播 |\n|---|---|\n| <img src=x onerror=evil()> | [点此](javascript:evil()) |');assert(!/<(?:img|a|script)\b/i.test(html));assert(html.includes('&lt;img'));
assert(!render('| 标题 | 内容 |\n|---|\n| 1 | 2 |').includes('<table>'));
assert(!render('```\n| 标题 | 内容 |\n|---|---|\n| 1 | 2 |\n```').includes('<table>'));
html=render('| 标题 | 内容 |\n|---|---|\n| 1 | 2 | 3 |');assert(html.includes('<p>| 1 | 2 | 3 |</p>'));
console.log('PASS: safe script/storyboard tables, escaped pipes, malformed-row fallback and code-fence preservation');
