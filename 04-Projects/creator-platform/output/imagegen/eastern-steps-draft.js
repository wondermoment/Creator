const baduanBreakdown=[
  {
    "id": "baduan-1",
    "name": "双手托天理三焦",
    "focus": "托起与放下",
    "how": "从自然站姿起，双手在身前缓缓上举，掌心朝上；在肩部舒适范围内伸展，再慢慢放下。",
    "avoid": "不耸肩、不锁肘，不为举高而后仰。"
  },
  {
    "id": "baduan-2",
    "name": "左右开弓似射雕",
    "focus": "向一侧开弓",
    "how": "取舒适浅站姿，双手从胸前向两侧展开，一手伸出、一手回拉；缓慢回收，再换方向。",
    "avoid": "膝盖朝脚尖方向，不蹲低、不用力拉扯肩颈。"
  },
  {
    "id": "baduan-3",
    "name": "调理脾胃须单举",
    "focus": "一手上托，一手下按",
    "how": "身体保持直立，一手掌心向上缓缓举起，另一手轻轻下按；回到身前后换侧。",
    "avoid": "不向一侧歪腰；肩部活动受限时降低举手高度。"
  },
  {
    "id": "baduan-4",
    "name": "五劳七伤往后瞧",
    "focus": "轻缓转头",
    "how": "站稳后保持躯干朝前，在舒适范围内慢慢向一侧转头，再回正换侧。",
    "avoid": "不甩头，不追求看到身后；颈痛、眩晕时停止。"
  },
  {
    "id": "baduan-5",
    "name": "摇头摆尾去心火",
    "focus": "浅站姿重心转移",
    "how": "初学示意采用浅站姿，双手轻放大腿，髋部微折，缓慢移动重心并小幅转动上身，再回正。",
    "avoid": "这是降低幅度的入门示意；不深蹲、不甩颈，完整动作请教练指导。"
  },
  {
    "id": "baduan-6",
    "name": "两手攀足固肾腰",
    "focus": "从髋部轻缓前倾",
    "how": "从直立开始，髋部轻缓折叠，双手沿大腿向膝部滑动，随后慢慢起身。",
    "avoid": "图示为不触脚的降低幅度版本；不强压腰背，骨质疏松或腰病先由专业人员调整。"
  },
  {
    "id": "baduan-7",
    "name": "攒拳怒目增气力",
    "focus": "轻握拳，缓慢推出",
    "how": "取舒适浅站姿，双拳轻收腰侧，一拳缓慢向前送出，再收回换侧。",
    "avoid": "肩膀放松、不锁肘，不需要瞪眼用力或憋气。"
  },
  {
    "id": "baduan-8",
    "name": "背后七颠百病消",
    "focus": "轻提脚跟，缓慢落下",
    "how": "双脚平行站稳，脚跟轻抬，再缓慢落地；重心保持平稳。",
    "avoid": "初学不震脚、不追求固定次数；平衡不好时扶稳支撑，停止不适动作。"
  }
];
const kungfuBreakdown=[
 {name:'站稳放松',how:'双脚自然站稳，膝盖微松，双臂先自然下垂。',avoid:'不用低位马步，不绷紧肩膀。'},
 {name:'分清拳与掌',how:'右手轻握拳，左手伸掌，先在胸前分开，确认左右手。',avoid:'拳头轻握即可，不用力攥紧。'},
 {name:'胸前抱拳',how:'左掌贴合右拳，放在胸前舒适位置，肩肘保持放松。',avoid:'不挤压手指，不耸肩；腕肩疼痛时跳过。'},
 {name:'缓慢放下',how:'停留片刻，双手松开并缓慢放下，回到自然站姿。',avoid:'动作顺畅即可，不追求速度和次数。'}
];
function easternStepCards(p){
 if(p.id==='baduan')return `<section class="eastern-breakdown"><h3>八式图解 · 逐式认识</h3><p class="small muted">每张图从左到右观察动作方向。第5、6、8式采用降低幅度的入门示意，不能替代完整套路教学；传统式名不代表治疗或延寿功效。</p>${baduanBreakdown.map((x,i)=>`<article class="eastern-step-card"><span class="chip">第 ${i+1} 式</span><h4>${x.name}</h4><img src="/static/assets/eastern/${x.id}-steps.webp" alt="赛博乔小乔演示${x.focus}的前后两个姿势" width="1536" height="1024" loading="lazy"><h5>${x.focus}</h5><p>${x.how}</p><p class="small muted">动作提醒：${x.avoid}</p></article>`).join('')}</section>`;
 if(p.id==='kungfu')return `<section class="eastern-breakdown"><h3>抱拳礼 · 四步拆解</h3>${kungfuBreakdown.map((x,i)=>`<article class="eastern-step-card"><span class="chip">步骤 ${i+1}</span><h4>${x.name}</h4><img src="/static/assets/eastern/kungfu-step-${i+1}.webp" alt="赛博乔小乔抱拳礼步骤${i+1}：${x.name}" loading="lazy"><p>${x.how}</p><p class="small muted">动作提醒：${x.avoid}</p></article>`).join('')}</section>`;
 return '';
}
