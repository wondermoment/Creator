from pathlib import Path
p=Path('frontend/customer-service.js');s=p.read_text('utf-8')
replacements={
 "${admin?`<button class=\"secondary\" data-inquiry-follow=\"${r.id}\">":"${admin?`<button class=\"secondary\" data-inquiry-follow=\"${r.id}\" ${inquiryLoading||inquiryError?'disabled':''}>",
 "${inquiryLoaded?'暂无已提交咨询。可在商品、酒店或诊所详情中发起咨询。':'正在读取咨询记录…'}":"${inquiryLoaded&&!inquiryLoading&&!inquiryError?'暂无已提交咨询。可在商品、酒店或诊所详情中发起咨询。':''}",
 '<button class="text-button" data-inquiry-refresh>刷新进度</button>':'${inquiryRefreshButton()}',
 '<button class="secondary" data-inquiry-refresh>刷新</button>':'${inquiryRefreshButton()}',
 '<p role="status">${esc(inquiryError)}</p>':'<p role="status">${esc(inquiryLoadStatus())}</p>',
 'function inquiryFollow(id){const r=':"function inquiryFollow(id){if(inquiryLoading||inquiryError){toast('请先刷新咨询进度，再更新记录');return}const r="
}
for old,new in replacements.items():
 assert old in s,old
 s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
p=Path('frontend/index.html');s=p.read_text('utf-8');assert 'customer-service.js?v=testing-sources-7' in s
p.write_text(s.replace('customer-service.js?v=testing-sources-7','customer-service.js?v=inquiry-load-8'),encoding='utf-8')
