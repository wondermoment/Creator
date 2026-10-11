from pathlib import Path
p=Path('frontend/customer-service.js');s=p.read_text('utf-8')
pairs=[
 ("function serviceInquiry(subject,draft){const key=crypto.randomUUID();", "function serviceInquiry(subject,draft){const key=crypto.randomUUID();let submitted=null;"),
 ("async f=>{await post('/commerce/inquiries',{request_key:key,subject,kind:f.get('kind'),need:f.get('need')});await loadInquiries()}", "async f=>{const body={request_key:key,subject,kind:String(f.get('kind')||'').trim(),need:String(f.get('need')||'').trim()};if(!body.need)throw Error('请填写咨询需求');if(submitted&&JSON.stringify(body)!==JSON.stringify(submitted))throw Error('上次提交结果待核对，请先关闭窗口并刷新咨询进度；不要修改内容后重复提交');submitted=body;await inquiryWrite('/commerce/inquiries','POST',submitted);await loadInquiries()}"),
 ("const r=inquiryRows.find(x=>x.id===id);if(!r)return;showForm('更新咨询进度'", "const r=inquiryRows.find(x=>x.id===id);if(!r)return;let uncertain=false;showForm('更新咨询进度'"),
 ("async f=>{await api('/commerce/inquiries/'+id,{method:'PATCH',body:JSON.stringify({...Object.fromEntries(f),expected_version:r.timeline.length})});await loadInquiries()}", "async f=>{if(uncertain)throw Error('上次保存结果待核对，请关闭窗口并刷新咨询进度后再操作');const body={...Object.fromEntries(f),expected_version:r.timeline.length};body.note=String(body.note||'').trim();if(!body.note)throw Error('请填写给客户的进度说明');try{await inquiryWrite('/commerce/inquiries/'+id,'PATCH',body)}catch(e){uncertain=true;inquiryError='上次进度保存结果待核对，请刷新后再操作';renderInquiries();throw e}await loadInquiries()}")
]
for old,new in pairs:
 assert old in s,old
 s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
p=Path('frontend/index.html');s=p.read_text('utf-8');assert 'customer-service.js?v=inquiry-load-8' in s
p.write_text(s.replace('customer-service.js?v=inquiry-load-8','customer-service.js?v=inquiry-write-9'),encoding='utf-8')
