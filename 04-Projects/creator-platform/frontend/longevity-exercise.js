const longevityMoves=[
{id:'chair',name:'椅子坐站',tag:'腿臀力量',dose:'先做 5—8 次 × 1 组',steps:['把稳固、不带轮的椅子靠墙，双脚与髋同宽。','身体略向前倾，呼气时用双腿站起；需要时扶牢扶手。','缓慢坐回，不向后跌坐。先用较高座椅降低难度。'],note:'膝痛或站不稳时停止；不要使用会滑动的椅子。'},
{id:'wall',name:'靠墙俯卧撑',tag:'上肢抗阻',dose:'先做 5—8 次 × 1 组',steps:['面对墙站稳，双手放在约胸高处，比肩略宽。','屈肘让身体缓慢靠近墙面，躯干保持自然直线。','呼气推回，肩膀放松；站近一些更容易。'],note:'腕肩疼痛时跳过。不要塌腰或憋气。'},
{id:'row',name:'坐姿弹力带划船',tag:'背部力量',dose:'轻阻力 6—10 次 × 1 组',steps:['使用完好的弹力带和厂家认可的牢固固定点，先检查是否有裂口。','坐稳，双脚落地，双手握带，肘部靠近身体向后拉。','肩膀远离耳朵，慢慢回位，不猛拉猛放。'],note:'不会固定弹力带时先请教练示范；不要套在松动物品上或对着脸拉伸。'},
{id:'heel',name:'扶椅提踵',tag:'小腿力量',dose:'先做 6—10 次 × 1 组',steps:['扶住牢固台面，双脚平行站稳。','缓慢抬起脚跟，重心均匀，保持自然呼吸。','缓慢放下，脚跟落地后再重复。'],note:'不要闭眼练或在台阶边缘练；有跌倒风险者先咨询康复人员。'},
{id:'walk',name:'饭后轻松走',tag:'日常活动',dose:'从 5—10 分钟开始',steps:['饭后按自己的舒适程度出发，不强求固定分钟数。','选择平坦、照明良好的路线，以能正常说话的速度走。','当天疲劳就缩短路线；可分成几次完成。'],note:'使用胰岛素或可致低血糖药物者，先与医生商量运动安排。'},
{id:'break',name:'久坐间隙动一动',tag:'办公小方法',dose:'每隔 30—60 分钟尝试起身',steps:['工作间隙站起，舒展肩膀或走去接水。','用 2—3 分钟轻走代替持续坐着；不方便站立可活动脚踝。','把小休息与日常任务连接，按身体耐受调整。'],note:'这是帮助减少久坐的习惯建议，不是人人必须遵守的医学处方。'}
];
const exerciseDetails={
chair:{benefit:'练习大腿和臀部发力，让起身、上下楼这些日常动作更轻松。',schedule:'每周 2—3 天，隔天练。先做 1 组，适应后逐步增加至 2 组。',illustration:'/static/assets/exercise/chair-sequence-qiao.webp',caption:'A 坐稳 → B 前倾起身 → C 站直。练习时把稳固座椅靠墙，双脚踩实。',video:'1763916272001'},
wall:{benefit:'练习胸部、肩部与上臂力量，帮助日常推门、撑起身体。靠墙版本比地面俯卧撑负担小。',schedule:'每周 2—3 天，隔天练。动作稳定后再把双脚稍微向后移，不急着增加难度。',illustration:'/static/assets/exercise/wall-pose-qiao.webp',caption:'屈肘靠近墙面，脚跟踩实，肩膀放松；再缓慢推回。',video:'1763919379001'},
row:{illustration:'/static/assets/exercise/row-qiao.webp',caption:'坐稳，双脚踩实，肘部贴近身体向后拉；练习时目光朝前，不转头。',benefit:'练习上背部和手臂力量，帮助日常拉取物品；不能靠这一个动作纠正所有体态问题。',schedule:'每周 2 天，间隔休息。先用最轻阻力，动作不晃动后再增加。'},
heel:{benefit:'练习小腿肌肉，支持行走时蹬地和踝关节控制。它不能单独替代平衡训练。',schedule:'每周 2—3 天，从双脚、有支撑开始。酸痛明显时先休息。',illustration:'/static/assets/exercise/heel-sequence-qiao.webp',caption:'A 双脚站稳 → B 缓慢抬起脚跟，再缓慢放下。扶手或椅子须稳固、不滑动。',video:'1763919414001',videoNote:'视频为坐站加提踵的组合进阶动作。初学者只参考提踵部分，按本页扶稳版本练习，不必跟做组合。'},
walk:{illustration:'/static/assets/exercise/walk-qiao.webp',caption:'选择平坦路线，放松肩膀，自然迈步，以能正常说话的速度走。',benefit:'增加日常活动量。持续、适量的步行有助心肺健康，也可能改善情绪和睡眠；不是吃多后的惩罚。',schedule:'身体舒适时可每天安排，先 5—10 分钟，再逐渐延长。不要求每天达到同样时长。'},
break:{illustration:'/static/assets/exercise/break-qiao.webp',caption:'工作间隙起身，轻走或舒展，给身体一点活动时间。',benefit:'打断长时间静坐，让活动分散到全天；短暂起身不能完全代替有氧或力量训练。',schedule:'工作日按自己的节奏重复。每次轻走 2—3 分钟，不必追求出汗。'}
};
function exerciseMedia(p,d){return `${d.illustration?`<figure style="margin:18px 0"><img src="${d.illustration}" alt="赛博乔小乔 · ${p.name}动作示意" loading="lazy" style="width:100%;height:auto;border-radius:14px"><figcaption class="small muted">${d.caption||'配合下方动作步骤阅读。'}</figcaption></figure>`:d.photo?`<figure style="margin:18px 0"><img src="https://assets.nhs.uk/nhsuk-cms/images/STRENGTH_EXERCISES-_${d.photo}.width-640.jpg" alt="${p.name}真人动作分解" loading="lazy" style="width:100%;height:auto;border-radius:14px"><figcaption class="small muted">动作分解参考 · NHS</figcaption></figure>`:'<p class="small muted">本项先按下方图文步骤学习，动作演示图正在补充核验。</p>'}${d.video?`<h3>真人视频 · 观察动作</h3><iframe title="${p.name} NHS 官方演示视频" src="https://players.brightcove.net/79855382001/EkC1XU82e_default/index.html?videoId=${d.video}" loading="lazy" allow="fullscreen" allowfullscreen style="width:100%;aspect-ratio:16/9;border:0;border-radius:14px"></iframe><p class="small muted">${d.videoNote||'NHS 官方英语演示，配合本页中文动作要点阅读。'} 外部视频加载受网络影响。</p><a class="text-button" href="https://www.nhs.uk/live-well/exercise/strength-and-flex-exercise-plan-how-to-videos/" target="_blank" rel="noopener noreferrer">无法播放？查看官方演示页面 ↗</a>`:'<p class="small muted">对应教学视频待核验，暂不提供未经核对的跟练视频。</p>'}`}
let longevityMove=null;
function longevityExercisePage(){const p=longevityMoves.find(x=>x.id===longevityMove);if(!p)return longevityExerciseLibrary();const d=exerciseDetails[p.id];return `<button class="art-back" data-exercise-back>← 全部长寿运动</button><section class="journey-card"><div class="journey-body"><span class="chip">${p.tag} · 入门指南</span><h3>${p.name}</h3><h4>有什么帮助</h4><p>${d.benefit}</p><h4>怎么安排练习</h4><p>${d.schedule}</p>${exerciseMedia(p,d)}<h4>中文动作要点</h4><span class="chip">${p.dose}</span><ol class="calm-design-steps">${p.steps.map(x=>`<li>${x}</li>`).join('')}</ol><p class="notice">${p.note}</p><details><summary>怎么安排一周的练习？</summary><p>${exerciseWeeklyAdvice(p.id)}</p><p>世界卫生组织建议成年人每周累计 150—300 分钟中等强度活动，并至少 2 天练习主要肌群。它是逐步接近的公共健康目标，不是初学者第一周的任务。</p></details><p class="small muted">以上适合一般健康成年人入门。术后、孕期、心血管疾病或明显关节问题请先由专业人员调整方案。胸痛、明显头晕或异常气促立即停止，必要时急救。</p><button class="btn primary" data-exercise-question>提问：怎么调整我的练习？</button><p class="small muted">依据：WHO《身体活动和久坐行为指南》（2020）。图文科普不等同于个体运动处方。</p></div></section>`}
document.addEventListener('click',e=>{const b=e.target.closest('[data-longevity-move]');if(b){longevityMove=b.dataset.longevityMove;render();document.getElementById('app')?.scrollIntoView({block:'start'})}if(e.target.closest('[data-exercise-back]')){longevityMove=null;render()}if(e.target.closest('[data-exercise-question]')){const question=exerciseCoachQuestion(longevityMove);if(question)openCoach('qiao',question)}});

const exerciseCardCopy={chair:['起身更有力量','每周 2—3 天'],wall:['从推墙开始，练上肢力量','每周 2—3 天'],row:['轻轻一拉，练习背部力量','每周 2 天'],heel:['稳稳提踵，照顾小腿力量','每周 2—3 天'],walk:['走慢一点，把活动带进生活','每天 5—10 分钟起'],break:['给久坐按个暂停键','间隙活动 2—3 分钟']};
function longevityExerciseLibrary(){return `<section class="exercise-library-intro"><span class="eyebrow">MOVE A LITTLE · LIVE WELL</span><h2>每天一点，把力量留住。</h2><p>选一个适合自己的小练习，慢慢开始。</p></section><div class="art-grid exercise-library">${longevityMoves.map(p=>`<button class="art-entry exercise-entry exercise-${p.id}" data-longevity-move="${p.id}" aria-label="查看${p.name}练习指南"><div class="art-cover"><img src="/static/assets/exercise/${p.id}-qiao.webp" alt="赛博乔小乔 · ${p.name}主题插画" width="960" height="640" loading="lazy"><span>${p.tag}</span></div><div class="art-entry-copy"><h2>${p.name}<span aria-hidden="true">→</span></h2><p>${exerciseCardCopy[p.id][0]}</p><small>${exerciseCardCopy[p.id][1]}</small><strong>查看练习指南</strong></div></button>`).join('')}</div><p class="art-note">抗阻练习留出休息日，轻量日常活动按身体感受安排。</p>`}

function exerciseWeeklyAdvice(id){
 if(id==='walk')return '先选择身体舒适的日子，轻松走 5—10 分钟，以能正常说话为准。疲劳时缩短路线，也可以分次完成；不必按力量练习的组数和间隔日安排。逐渐增加活动量，不把运动当成补偿进食的任务。';
 if(id==='break')return '把短暂活动分散到工作日：在任务切换时轻走 2—3 分钟，或按身体情况活动脚踝、肩膀。不需要凑够组数，也不用追求出汗；短暂活动不能完全代替有氧和力量训练。';
 return '一般成年人可从每周 2 天的力量练习开始，相同肌群安排间隔休息。先热身 3—5 分钟，每组后休息约 1—2 分钟，以还能再做 2—3 次的轻松程度收尾。动作稳定且次日无明显不适后，再逐步增加次数或阻力。';
}
function exerciseCoachQuestion(id){
 const p=longevityMoves.find(x=>x.id===id);if(!p)return '';
 const d=exerciseDetails[id];
 return `我正在阅读「${p.name}」入门指南。页面建议：${d.schedule} 注意：${p.note} 请围绕这个练习，先了解我的运动基础、身体限制和可用环境，再帮我调整练习方法与安排。不要假设我的病史；出现急症征兆时先建议停止练习并及时求助。`;
}
