const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const c={document:{addEventListener(){}},window:{addEventListener(){}},additionalLongevitySkills:[],esc:x=>String(x),travelStored:()=>[]};
vm.createContext(c);for(const f of ['diet','lifestyle-additions','recipe-expansion'])vm.runInContext(fs.readFileSync('frontend/'+f+'.js','utf8'),c);
const meals=vm.runInContext('meals',c),ids=vm.runInContext('recipeHandwrittenIds',c);
assert.equal(ids.length,26);assert.equal(meals.length,26);for(const id of ids){const meal=meals.find(x=>x.id===id),html=c.foodRecipe(meal);assert.ok(html.includes(id+'-ingredients-handwritten.webp'));assert.ok(!html.includes('STEP 1'));for(const step of meal.steps)assert.ok(html.includes(step));for(const match of c.recipeFlow(meal).matchAll(/src="\/static\/([^\"]+)"/g))assert.ok(fs.existsSync('frontend/'+match[1]),'Missing '+match[1]);assert.equal((c.recipeFlow(meal).match(/<img /g)||[]).length,4);}
console.log(`PASS: ${ids.length} actual integrated recipes; image files exist, step text retained, no duplicate lists or nonexistent step images. Synthetic only.`);

