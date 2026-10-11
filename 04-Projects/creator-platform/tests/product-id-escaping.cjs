const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const esc=v=>String(v??'').replace(/[&<>"']/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
const ctx={esc,money:n=>String(n),shopFilter:'全部',document:{addEventListener(){}},window:{addEventListener(){}}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('frontend/product-editor.js','utf8'),ctx);
for(const id of ['custom-" autofocus onfocus="alert(1)', 'custom-<svg onload=alert(1)>', "custom-a'&?#", 'custom-normal_123']){
  ctx.fixture={id,name:'合成 <商品>',category:'食物',description:'合成测试说明',ingredients:'合成规格',usage:'合成用法',cautions:'合成限制',price:100,stock:1,status:'published',has_image:true};
  const parts=vm.runInContext('managedProducts=[fixture]; [managedCatalog(),managedShopCards(),managedDetail(fixture)]',ctx);
  for(const attr of ['data-product-edit','data-product-image','data-product-preview']){
    const value=parts[0].match(new RegExp(attr+'="([^"]*)"'))?.[1];
    assert.equal(value,esc(id),attr+' must preserve the complete ID inside one escaped attribute');
  }
  assert.equal(parts[2].match(/data-shop-buy="([^"]*)"/)?.[1],esc(id));
  assert.ok(parts[1].includes('href="#shop/'+encodeURIComponent(id)+'"'));
  for(const html of parts){
    assert.ok(!html.includes('<svg onload='));
    assert.ok(!html.includes(' autofocus onfocus="'));
    assert.ok(html.includes('/api/commerce/products/'+encodeURIComponent(id)+'/image'));
    assert.ok(html.includes('合成 &lt;商品&gt;'));
  }
}
console.log('PASS: catalog actions, shop links, detail buy button and image URLs contain escaped/encoded legacy IDs');
