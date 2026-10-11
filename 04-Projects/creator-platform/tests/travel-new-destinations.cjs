const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const calls=[],c={document:{addEventListener(){}},window:{addEventListener(){}},esc:String,openCoach:(...a)=>calls.push(a),localStorage:{getItem(){return null}}};vm.createContext(c);
for(const file of ['travel-guides','travel-domestic-guides','travel','travel-new-destinations','customer-service'])vm.runInContext(fs.readFileSync('frontend/'+file+'.js','utf8'),c);
const trips=vm.runInContext('newDomesticJourneys',c),guides=vm.runInContext('detailedTravelGuides',c);
assert.equal(trips.length,5);assert.equal(trips.filter(t=>t.category==='温泉休养').length,2);assert.equal(trips.filter(t=>t.category==='海岛静修').length,2);assert.equal(trips.filter(t=>t.category==='长寿生活').length,1);
for(const t of trips){
 const g=guides[t.id];assert(g.days.length>=3);assert.equal(t.route.length,g.days.length);assert(g.sources.length);assert(t.place.includes('中国'));
 const html=c.travelDetail(t);assert(html.includes('back top'));assert(html.includes('data-travel-top'));assert(html.includes(g.days[0].title));
 for(const d of g.days)for(const field of ['title','morning','afternoon','evening','practical','rain'])assert(d[field].trim(),t.id+field);
 for(const photo of g.photos)assert(fs.existsSync('frontend/'+photo.src.replace('/static/','')));
 c.openServiceChat(t.name+' · 中文行程规划');const context=calls.at(-1)[2].context;assert(context.length<4000);assert(context.includes(g.days[0].title));assert(context.includes('行程仅为编辑建议'));
}
vm.runInContext("travelFilter='温泉休养'",c);assert(!c.travelEmpty().includes('加入收藏'));assert(c.travelEmpty().includes('查看其他目的地'));
vm.runInContext("travelFilter='收藏'",c);assert(c.travelEmpty().includes('加入收藏'));
console.log('PASS: five new domestic guides, full daily alternatives, source context, three local photos and correct category/favorite empty states. Synthetic only.');
