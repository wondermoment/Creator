'use strict';
// Read only an explicit shot table. Never infer timings or truncate script text.
function videoScriptScenes(source){
 const required=['short_video','video_storyboard','video_edit'].includes(source.repurpose_format);
 const clean=s=>s.trim().replace(/\*\*|__/g,'');
 const cells=line=>line.trim().replace(/^\|/,'').replace(/\|$/,'').split(/(?<!\\)\|/).map(s=>clean(s.replace(/\\\|/g,'|')));
 const lines=source.body.split(/\r?\n/),tables=[];
 for(let i=0;i<lines.length-1;i++){
  if(!lines[i].includes('|')||!/^\s*\|?\s*:?-{3,}/.test(lines[i+1]))continue;
  const head=cells(lines[i]),text=head.findIndex(x=>['字幕','画面字幕','画面重点文字'].includes(x));
  const time=head.findIndex(x=>['时间','时间段','起止秒数','时长'].includes(x));
  if(text<0||time<0)continue;
  const rows=[];let n=i+2;while(n<lines.length&&lines[n].includes('|')&&lines[n].trim()){rows.push(cells(lines[n++]));}
  tables.push({head,text,time,rows});i=n-1;
 }
 if(!tables.length){if(required)throw Error('请先在脚本中整理分镜表，包含“时间”或“时长”以及“字幕”列，再开始制作。');return null;}
 if(tables.length!==1)throw Error('发现多份分镜表，请在脚本中保留本次要制作的一份，再开始制作。');
 const {head,text,time,rows}=tables[0];
 if(!rows.length||rows.length>8)throw Error('分镜表需包含 1–8 个镜头，请先调整脚本；不会自动删减镜头。');
 let end=0;
 return rows.map((row,i)=>{
  if(row.length!==head.length)throw Error(`镜头 ${i+1} 的表格列数不符，请核对分镜表。`);
  const caption=row[text];if(!caption||caption.length>72)throw Error(`镜头 ${i+1} 的字幕需为 1–72 字，请先调整脚本；不会自动截断字幕。`);
  const stamp=row[time].replace(/秒|s/gi,'').replace(/\s+/g,'');let seconds;
  if(head[time]==='时长'&&/^\d+$/.test(stamp))seconds=Number(stamp);
  else{
   const range=stamp.match(/^(\d+)[-–—~～至](\d+)$/);
   if(!range||Number(range[1])!==end)throw Error(`镜头 ${i+1} 的时间需从 ${end} 秒连续开始，例如“${end}–${end+6}秒”。`);
   seconds=Number(range[2])-Number(range[1]);
  }
  if(!Number.isInteger(seconds)||seconds<3||seconds>12)throw Error(`镜头 ${i+1} 需为 3–12 秒，请先拆分或调整脚本。`);
  end+=seconds;return {text:caption,seconds,asset_id:'',start:0};
 });
}
