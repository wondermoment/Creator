// Restricted Markdown presentation: raw HTML stays text; only HTTP(S) links.
function chatInline(value){
 const input=String(value),link=/\[([^\[\]\n]+)\]\((https?:\/\/[^\s<>"()]+(?:\([^\s<>"()]*\)[^\s<>"()]*)*)\)/gi;
 let match,last=0,html='';
 while((match=link.exec(input))){
  let valid=false;try{const url=new URL(match[2]);valid=['https:','http:'].includes(url.protocol)&&!!url.hostname&&!url.username&&!url.password}catch{}
  if(!valid)continue;
  const href=match[2].replace(/[&"'<>]/g,c=>({'&':'&amp;','"':'&quot;',"'":'&#39;','<':'&lt;','>':'&gt;'}[c]));
  html+=chatInlineText(input.slice(last,match.index))+'<a href="'+href+'" target="_blank" rel="noopener noreferrer">'+chatInlineText(match[1])+'</a>';
  last=link.lastIndex;
 }
 return html+chatInlineText(input.slice(last));
}
function chatInlineText(value){
 const safe=String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 return safe.replace(/\*\*([^*\n]+)\*\*/g,'<strong>$1</strong>').replace(/__([^_\n]+)__/g,'<strong>$1</strong>').replace(/`([^`\n]+)`/g,'<code>$1</code>').replace(/(^|\s)\*([^*\n]+)\*(?=\s|[，。！？、,.!?]|$)/g,'$1<em>$2</em>');
}
function chatAnswer(value){
 const lines=String(value).replace(/\r\n?/g,'\n').split('\n');let html='',paragraph=[],list='',items=[];
 const flushParagraph=()=>{if(paragraph.length){html+='<p>'+paragraph.map(chatInline).join('<br>')+'</p>';paragraph=[]}};
 const flushList=()=>{if(list){html+=`<${list}>${items.join('')}</${list}>`;list='';items=[]}};
 for(const raw of lines){
  const line=raw.trim();
  if(!line){flushParagraph();continue}
  const heading=line.match(/^#{1,6}\s+(.+?)(?:\s+#+)?$/);
  const bullet=line.match(/^[-*+]\s+(.+)$/),ordered=line.match(/^\d+[.)、]\s+(.+)$/);
  if(heading){flushParagraph();flushList();html+='<h3>'+chatInline(heading[1])+'</h3>';continue}
  if(/^([-*_])(?:\s*\1){2,}$/.test(line)){flushParagraph();flushList();html+='<hr>';continue}
  if(bullet||ordered){flushParagraph();const type=ordered?'ol':'ul';if(list&&list!==type)flushList();list=type;const text=(ordered||bullet)[1];const label=text.match(/^([^：:*_`<>\n]{2,16})([：:])\s*(\S[\s\S]*)$/);items.push('<li>'+(label?'<strong>'+chatInline(label[1])+label[2]+'</strong> '+chatInline(label[3]):chatInline(text))+'</li>');continue}
  flushList();paragraph.push(line.replace(/^>\s?/,''));
 }
 flushParagraph();flushList();return '<div class="reading-answer">'+html+'</div>';
}
function chatMessageHtml(message){return message.role==='assistant'?chatAnswer(message.content):`<p class="chat-question" style="white-space:pre-wrap">${esc(message.content)}</p>`}
