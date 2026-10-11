/* Human-readable request failures; never echo validation input values. */
function requestErrorMessage(data,status){
 if(typeof data?.detail==='string'&&data.detail.trim())return data.detail;
 const labels={question:'问题',history:'对话记录',value:'测量值',observed_at:'测量时间',source:'来源',file:'文件',reason:'复核说明',review:'复盘内容',quantity:'数量',title:'标题',price:'价格',stock:'库存',name:'名称'};
 if(Array.isArray(data?.detail)){
  const messages=data.detail.slice(0,3).map(item=>{
   const field=(item.loc||[]).filter(x=>!['body','query','path'].includes(x)).find(x=>labels[x]);
   const label=labels[field]||'填写内容';
   const limit=item.ctx?.min_length??item.ctx?.max_length;
   if(item.type==='missing')return label+'不能为空';
   if(item.type==='string_too_short')return label+'至少需要 '+limit+' 个字符';
   if(item.type==='string_too_long')return label+'不能超过 '+limit+' 个字符';
   if(['float_parsing','int_parsing','finite_number','float_type','int_type'].includes(item.type))return label+'请填写有效数字';
   if(item.type==='literal_error'||item.type==='enum')return label+'请从可选项中选择';
   if(typeof item.msg==='string'&&/[\u3400-\u9fff]/.test(item.msg))return item.msg.replace(/^Value error,\s*/,'');
   return label+'格式不正确，请检查后重试';
  });
  if(messages.length)return [...new Set(messages)].join('；');
 }
 return ({413:'文件或内容过大，请缩小后重试',429:'请求较多，请稍后再试',503:'服务暂时不可用，请稍后重试'})[status]||'请求未能完成，请稍后重试';
}
