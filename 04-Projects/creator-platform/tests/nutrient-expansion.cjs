const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const c={document:{addEventListener(){}},esc:String,location:{hash:''}};vm.createContext(c);
for(const f of ['nutrient-articles.js','nutrient-flow.js','nutrients.js','nutrient-additions.js'])vm.runInContext(fs.readFileSync('frontend/'+f,'utf8'),c);
assert.equal(vm.runInContext('nutrientItems.length',c),12);
for(let i=0;i<12;i++){
 const html=c.nutrientArticlePage(i);assert.ok(html.includes('全球期刊'));
 assert.ok(html.includes(`data-nutrient-index="${i}"`));
 const srcs=[...html.matchAll(/<img src="([^"]+)"/g)].map(m=>m[1]);
 assert.equal(srcs.length,4);
 for(const src of srcs)assert.ok(fs.existsSync('frontend/'+src.replace('/static/','')),src);
 const opts=c.nutrientConsultOptions(i);assert.ok(opts.context.length<4000);assert.ok(opts.context.includes(opts.sources[0].url));
 assert.ok(opts.context.includes('没有保存、购买、预约执行工具'));
 c.nutrientDetail(i);assert.equal(c.location.hash,'diet/nutrient-'+i);
}
vm.runInContext(fs.readFileSync('frontend/skill-quality.js','utf8'),c);
vm.runInContext(fs.readFileSync('frontend/diet.js','utf8'),c);
for(let i=6;i<12;i++){c.location.hash='#diet/nutrient-'+i;assert.equal(c.foodPage(),c.nutrientArticlePage(i))}
for(const [category,count] of [['全部',12],['肌肉与体能',2],['骨骼健康',2],['肠道与代谢',1],['基础营养',3],['前沿研究',4]]){
 vm.runInContext('nutrientFilter='+JSON.stringify(category),c);
 assert.equal([...c.nutrientGuide().matchAll(/data-nutrient-detail=/g)].length,count);
}
assert.ok(c.nutrientArticlePage(99).includes('未找到'));
console.log('PASS: 12 full articles and routes, 48 image references, category counts, research-aware consultation context; no real model calls.');
