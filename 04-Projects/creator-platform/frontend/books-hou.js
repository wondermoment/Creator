/* Bibliographic titles transcribed from the user-supplied article; not full-text copies. */
const houBooks=[
  {
    "id": "hou-1",
    "number": 1,
    "title": "人类简史：从动物到上帝",
    "category": "生命基础"
  },
  {
    "id": "hou-2",
    "number": 2,
    "title": "未来简史",
    "category": "生命基础"
  },
  {
    "id": "hou-3",
    "number": 3,
    "title": "人体简史",
    "category": "生命基础"
  },
  {
    "id": "hou-4",
    "number": 4,
    "title": "绝佳时间",
    "category": "生命基础"
  },
  {
    "id": "hou-5",
    "number": 5,
    "title": "生命：非常的世界",
    "category": "生命基础"
  },
  {
    "id": "hou-6",
    "number": 6,
    "title": "长寿：当人类不再衰老",
    "category": "长寿抗衰"
  },
  {
    "id": "hou-7",
    "number": 7,
    "title": "超越百岁：长寿的科学与艺术",
    "category": "长寿抗衰"
  },
  {
    "id": "hou-8",
    "number": 8,
    "title": "老而不衰的科学",
    "category": "长寿抗衰"
  },
  {
    "id": "hou-9",
    "number": 9,
    "title": "不老时代：年轻又长寿的科学和方法",
    "category": "长寿抗衰"
  },
  {
    "id": "hou-10",
    "number": 10,
    "title": "长寿：逆转衰老的科学饮食",
    "category": "长寿抗衰"
  },
  {
    "id": "hou-11",
    "number": 11,
    "title": "长寿的习惯",
    "category": "长寿抗衰"
  },
  {
    "id": "hou-12",
    "number": 12,
    "title": "衰老生物学",
    "category": "长寿抗衰"
  },
  {
    "id": "hou-13",
    "number": 13,
    "title": "基因传：众生之源",
    "category": "基因"
  },
  {
    "id": "hou-14",
    "number": 14,
    "title": "遗传的革命",
    "category": "基因"
  },
  {
    "id": "hou-15",
    "number": 15,
    "title": "DNA：生命的秘密",
    "category": "基因"
  },
  {
    "id": "hou-16",
    "number": 16,
    "title": "垃圾DNA",
    "category": "基因"
  },
  {
    "id": "hou-17",
    "number": 17,
    "title": "细胞传",
    "category": "细胞"
  },
  {
    "id": "hou-18",
    "number": 18,
    "title": "细胞简史",
    "category": "细胞"
  },
  {
    "id": "hou-19",
    "number": 19,
    "title": "线粒体与生命的意义",
    "category": "细胞"
  },
  {
    "id": "hou-20",
    "number": 20,
    "title": "端粒：年轻、健康、长寿的新科学",
    "category": "细胞"
  },
  {
    "id": "hou-21",
    "number": 21,
    "title": "大脑能量",
    "category": "细胞"
  },
  {
    "id": "hou-22",
    "number": 22,
    "title": "分子营养",
    "category": "分子营养"
  },
  {
    "id": "hou-23",
    "number": 23,
    "title": "功能医学",
    "category": "功能医学"
  },
  {
    "id": "hou-24",
    "number": 24,
    "title": "癌症传：众病之王",
    "category": "癌症"
  },
  {
    "id": "hou-25",
    "number": 25,
    "title": "癌症·防御",
    "category": "癌症"
  },
  {
    "id": "hou-26",
    "number": 26,
    "title": "威廉姆斯内分泌学",
    "category": "内分泌"
  },
  {
    "id": "hou-27",
    "number": 27,
    "title": "人为什么会生病",
    "category": "内分泌"
  },
  {
    "id": "hou-28",
    "number": 28,
    "title": "人类代谢调控",
    "category": "代谢"
  },
  {
    "id": "hou-29",
    "number": 29,
    "title": "酶与诺贝尔奖",
    "category": "代谢"
  },
  {
    "id": "hou-30",
    "number": 30,
    "title": "酶学方法",
    "category": "代谢"
  },
  {
    "id": "hou-31",
    "number": 31,
    "title": "战斗细胞",
    "category": "免疫"
  },
  {
    "id": "hou-32",
    "number": 32,
    "title": "炎症：食物、微生物和疾病的故事",
    "category": "免疫"
  },
  {
    "id": "hou-33",
    "number": 33,
    "title": "抗炎从根源上逆转慢病的炎症消除方案",
    "category": "免疫"
  },
  {
    "id": "hou-34",
    "number": 34,
    "title": "肠道菌群与衰老",
    "category": "微生物"
  },
  {
    "id": "hou-35",
    "number": 35,
    "title": "肠道菌群与精准营养健康",
    "category": "微生物"
  },
  {
    "id": "hou-36",
    "number": 36,
    "title": "第二大脑",
    "category": "微生物"
  },
  {
    "id": "hou-37",
    "number": 37,
    "title": "你的皮肤屏障90%可以靠营养修复",
    "category": "微生物"
  },
  {
    "id": "hou-38",
    "number": 38,
    "title": "中西医结合临床",
    "category": "中医"
  },
  {
    "id": "hou-39",
    "number": 39,
    "title": "运动改造大脑",
    "category": "运动心理"
  },
  {
    "id": "hou-40",
    "number": 40,
    "title": "情绪的毒 身体知道",
    "category": "运动心理"
  },
  {
    "id": "hou-41",
    "number": 41,
    "title": "持续的幸福",
    "category": "运动心理"
  },
  {
    "id": "hou-42",
    "number": 42,
    "title": "冥想：身心放松的力量",
    "category": "运动心理"
  },
  {
    "id": "hou-43",
    "number": 43,
    "title": "当下的力量",
    "category": "运动心理"
  },
  {
    "id": "hou-44",
    "number": 44,
    "title": "能量的真相",
    "category": "运动心理"
  }
];
houBooks.unshift(
 {id:'new-longevity-singularity',number:45,title:'长寿奇点',category:'AI与未来',edition:'张见一 · 浙江大学出版社 · 用户提供实拍书封'},
 {id:'new-noma',number:46,title:'NOMA餐厅发酵指南',category:'营养饮食',edition:'René Redzepi / David Zilber · 广东旅游出版社 · 用户提供实拍书封'},
);
let bookCategory='全部',bookSearch='';
function savedBooks(){return travelStored('wld-book-favorites',[])}
houBooks.splice(2,0,...[{"id": "new-synthetic-biology", "number": 48, "title": "合成生物：生命的编程艺术", "category": "生命科技", "edition": "中国科学技术出版社"}, {"id": "new-singularity-nearer", "number": 49, "title": "奇点更近", "category": "AI与未来", "edition": ""}, {"id": "new-microbiome-master-key", "number": 50, "title": "终身活力：用微生物组开启全面健康", "category": "微生物", "edition": "华龄出版社"}, {"id": "new-what-is-health", "number": 51, "title": "何谓健康", "category": "身心健康", "edition": "上海科技教育出版社"}, {"id": "new-super-agers", "number": 52, "title": "长寿真相：保持年轻和活力的关键策略", "category": "长寿抗衰", "edition": "中信出版集团"}, {"id": "new-we-are-as-gods", "number": 53, "title": "吾辈如神", "category": "AI与未来", "edition": ""}, {"id": "new-getting-older", "number": 54, "title": "变老之前要知道的事", "category": "健康养老", "edition": "广东人民出版社"}, {"id": "new-biomanufacturing", "number": 55, "title": "生命造万物", "category": "生命科技", "edition": "电子工业出版社"}]);
function longevityBooksPage(){const saved=savedBooks();const list=houBooks.filter(b=>(bookCategory==='全部'||(bookCategory==='收藏'?saved.includes(b.id):b.category===bookCategory))&&b.title.toLowerCase().includes(bookSearch.toLowerCase()));return `<section class="travel-intro"><div class="eyebrow">LONGEVITY / READING</div><h1>长寿知识，从一本书开始。</h1><p>侯博士推荐 44 本 · 扩展阅读 ${houBooks.length-44} 本</p></section><div class="book-search-row"><input id="book-search" aria-label="搜索书名" placeholder="搜索书名" maxlength="100" value="${esc(bookSearch)}" style="min-width:0"><button class="primary" data-book-search>搜索</button></div><details class="book-filters"><summary>书籍分类 · ${esc(bookCategory)} <span>展开筛选</span></summary><div class="food-region-tabs" aria-label="书籍分类">${['全部','收藏',...new Set(houBooks.map(b=>b.category))].map(c=>`<button data-book-category="${c}" class="${bookCategory===c?'active':''}" aria-pressed="${bookCategory===c}">${c}</button>`).join('')}</div></details><p class="small muted">当前 ${list.length} 本</p><div class="book-waterfall">${[0,1].map(col=>`<div class="book-waterfall-column">${list.filter((_,i)=>i%2===col).map(b=>`<article class="card book-tile"><button class="book-save" data-book-favorite="${b.id}" aria-label="${saved.includes(b.id)?'取消收藏':'收藏'}${esc(b.title)}" aria-pressed="${saved.includes(b.id)}">${saved.includes(b.id)?'♥':'♡'}</button><span class="chip">${esc(b.category)}</span><div class="book-media"><div class="book-cover-slot">${bookMetadata[b.id]?.cover?`<img src="${bookMetadata[b.id].cover}" alt="${esc(b.title)}书封 · ${esc(bookMetadata[b.id]?.source||'公众号书单所示版本')}" loading="lazy" width="150" height="210">`:`<div class="book-cover-pending">${esc(b.title)}<small>封面待核对</small></div>`}</div><div class="book-icon-actions"><button data-book-reader="${b.id}" aria-label="提问：${esc(b.title)}" title="提问"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M4 4h16v12H9l-5 4Z"/><path d="M8 8h8M8 12h5"/></svg><span>提问</span></button><button data-book-insights="${b.id}" aria-label="核心知识点：${esc(b.title)}" title="核心知识点"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M9 18h6M10 21h4M8 14a6 6 0 1 1 8 0l-1 2H9Z"/></svg><span>知识点</span></button>${bookWereadLink(b)}</div></div><h2 class="book-title">${esc(b.title)}</h2><p class="book-author">${esc(bookMetadata[b.id]?.author||(b.id==='new-longevity-singularity'?'张见一':b.id==='new-noma'?'René Redzepi · David Zilber':'作者与版本待核对'))}</p><p class="book-intro">${esc(bookMetadata[b.id]?.intro||(b.id==='new-noma'?'聚焦发酵原理与厨房实践。具体操作应依据原书配方，核对盐度、温度与卫生条件。':'未收录于这篇公众号书单，上传原文后可提炼核心观点。'))}</p></article>`).join('')}</div>`).join('')}${list.length?'':'<section class="card">暂无匹配书目，可切换分类或修改搜索词。</section>'}</div>`}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;try{if(b.dataset.bookCategory){bookCategory=b.dataset.bookCategory;render()}if(b.hasAttribute('data-book-search')){bookSearch=document.getElementById('book-search').value.trim();render()}if(b.dataset.bookFavorite){const old=savedBooks(),id=b.dataset.bookFavorite;travelSave('wld-book-favorites',old.includes(id)?old.filter(x=>x!==id):[...old,id]);render()}}catch{toast('收藏未能保存，请检查浏览器存储')}});
document.addEventListener('keydown',e=>{if(e.target.id==='book-search'&&e.key==='Enter'){e.preventDefault();bookSearch=e.target.value.trim();render()}});

houBooks.unshift(...[{"id": "zhang-running", "number": 56, "title": "跑步治愈", "category": "运动心理", "edition": "跑步治愈"}, {"id": "zhang-control", "number": 57, "title": "掌控", "category": "运动心理", "edition": "掌控：重启不疲惫、不焦虑的人生（经典修订版）"}]);
