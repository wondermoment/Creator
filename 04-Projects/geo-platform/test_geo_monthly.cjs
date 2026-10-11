const fs=require('fs'),vm=require('vm'),assert=require('assert');
const ctx=vm.createContext({Date,Map,Set,JSON,document:{addEventListener(){}}});
vm.runInContext(fs.readFileSync('static/geo-monthly.js','utf8'),ctx);
const s=(date,mentioned,overrides={})=>({platform:'豆包',question:'如何选型',answer:'实际记录',source:'manual',observed_at:date,mentioned,citation:'',...overrides});
ctx.reports=[{status:'sample',samples:[s('2026-09-01T00:00:00Z',true)]},{status:'manual',samples:[
 s('2026-08-31T16:00:00Z',true),s('2026-09-15T01:00:00Z',false),
 s('2026-09-15T01:00:00Z',false), // duplicate observation
 s('2026-10-02T00:00:00Z',true,{citation:'https://example.com',recommended:true}),
 s('2026-10-02T01:00:00Z',true,{question:'不同问题'}),
 s('2026-10-02T01:00:00Z',true,{source:'api'}),s('bad',true),s('2028-01-01T00:00:00Z',true)
]}];
let r=vm.runInContext("geoMonthlyData(reports,'',new Date('2026-11-10T00:00:00Z'))",ctx);
assert.equal(r.rows.length,3);assert.equal(r.rows[0].samples,0);assert.equal(r.rows[0].rate,null);
assert.equal(r.rows[1].samples,2);assert.equal(r.rows[1].paired,1);assert.equal(r.rows[1].delta,100);
assert.equal(r.rows[1].recommendationKnown,1);assert.equal(r.rows[2].samples,2);assert.equal(r.rows[2].rate,50);
assert.equal(r.skipped,2);
assert.equal(vm.runInContext("geoMonthlyData(reports,'Kimi',new Date('2026-11-10T00:00:00Z')).rows.length",ctx),0);
assert.equal(vm.runInContext("geoMonthKey('2026-08-31T16:00:00Z')",ctx),'2026-09');
assert.equal(vm.runInContext("geoMonthKey('2026-08-31')",ctx),null);
assert.equal(vm.runInContext("geoMonthKey('2026-02-30T00:00:00Z')",ctx),null);
ctx.zoneReports=[{status:'manual',samples:[
 s('2026-09-30T16:00:00Z',true),s('2026-10-01T00:00:00+08:00',true),
 s('2026-10-01T00:00:00.000+08:00',true),s('2026-10-01T01:00:00+08:00',false)
]}];
const zones=vm.runInContext("geoMonthlyData(zoneReports,'',new Date('2026-10-10T00:00:00Z'))",ctx);
assert.equal(zones.rows[0].samples,2,'same instant in different timezones is one observation');
assert.equal(zones.rows[0].rate,50,'timezone spelling must not inflate mention rate');
assert.equal(zones.duplicates,2);
ctx.conflictSamples=[s('2026-09-02T00:00:00Z',false),s('2026-10-02T00:00:00Z',true),s('2026-10-02T08:00:00+08:00',false)];
for(const reverse of [false,true]){
 ctx.ordered=reverse?[...ctx.conflictSamples].reverse():ctx.conflictSamples;
 const result=vm.runInContext("geoMonthlyData([{samples:ordered}],'',new Date('2026-10-10T00:00:00Z'))",ctx);
 assert.equal(result.rows[0].delta,null,'contradictory latest observations must not imply improvement');
 assert.equal(result.rows[0].paired,0);assert.equal(result.rows[0].conflicts,1);
}
ctx.ordered=[...ctx.conflictSamples,s('2026-10-03T00:00:00Z',true)];
const resolved=vm.runInContext("geoMonthlyData([{samples:ordered}],'',new Date('2026-10-10T00:00:00Z'))",ctx);
assert.equal(resolved.rows[0].delta,100);assert.equal(resolved.rows[0].conflicts,0);
ctx.ordered=[s('2026-09-02T00:00:00Z',false),s('2026-09-02T00:00:00Z',true),s('2026-10-02T00:00:00Z',true),
 s('2026-09-02T00:00:00Z',true,{question:'另一题'}),s('2026-10-02T00:00:00Z',false,{question:'另一题'})];
const partial=vm.runInContext("geoMonthlyData([{samples:ordered}],'',new Date('2026-10-10T00:00:00Z'))",ctx);
assert.equal(partial.rows[0].paired,1);assert.equal(partial.rows[0].delta,-100,'exclude previous-month conflicts; unaffected questions still compare');
console.log('PASS: timezone boundary, sample exclusion, exact deduplication, missing months, fixed-question comparison, unknown recommendation and platform filter');
