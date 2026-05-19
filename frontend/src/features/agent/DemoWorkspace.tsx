import { Clock3, Map, Menu, MessageSquareText, Pencil, Plus, Send, Sparkles, StickyNote } from 'lucide-react'
import type { CSSProperties } from 'react'

import { Button } from '@/components/ui/button'

type DemoWorkspaceProps = {
  onOpenSidebar: () => void
}

type BoardItem = {
  id: string
  x: number
  y: number
  width: number
  rotate?: number
  title: string
  body: string
  tone: string
}

type ImageItem = {
  id: string
  x: number
  y: number
  width: number
  rotate?: number
  title: string
  caption: string
  src: string
}

const mapAnchors = {
  hotel: { x: 34, y: 62, label: '黄龙 / 武林门' },
  westLake: { x: 53, y: 50, label: '西湖西线' },
  liangzhu: { x: 80, y: 53, label: '良渚' },
}

const messages = [
  {
    id: 'm1',
    role: 'user',
    content: '我想下个月去杭州玩三天，两个人，预算 3000 元，喜欢自然风景和本地美食，希望交通别太折腾。',
    time: '09:41',
  },
  {
    id: 'm2',
    role: 'assistant',
    content: '我先把偏好拆成几个判断：住哪里、每天走哪条线、哪些素材值得保留。右侧画板只整理位置和灵感，具体日程放到底部时间轴。',
    time: '09:42',
  },
  {
    id: 'm3',
    role: 'assistant',
    content: '第一版方向：住在黄龙或武林门，Day 1 轻量西湖，Day 2 做自然风景主线，Day 3 放良渚和返程缓冲。',
    time: '09:44',
  },
]

const quickActions = ['把 Day 2 换成九溪', '住宿再便宜一点', '减少打车', '餐饮更本地']

const boardItems = [
  {
    id: 'hotel',
    x: 54,
    y: 18,
    width: 172,
    rotate: 1,
    title: '住宿基点',
    body: '黄龙 / 武林门\n交通、餐饮和预算比较均衡',
    tone: '#f7fbff',
  },
  {
    id: 'food-tip',
    x: 82,
    y: 70,
    width: 188,
    rotate: 1,
    title: '餐饮 Tip',
    body: '避开排队型网红店\n优先小馆与老店\n晚餐不要离住宿太远',
    tone: '#fff5dc',
  },
  {
    id: 'confirm',
    x: 55,
    y: 78,
    width: 190,
    rotate: -1,
    title: '待确认',
    body: 'Day 2 灵隐半日是否太挤？\n备选：九溪 / 龙井茶村',
    tone: '#fff8d8',
  },
] satisfies BoardItem[]

const imageItems = [
  {
    id: 'west-lake-photo',
    x: 36,
    y: 17,
    width: 148,
    rotate: 1,
    title: '西湖西线',
    caption: 'Day 1 轻量散步',
    src: 'https://images.unsplash.com/photo-1565967511849-76a60a516170?auto=format&fit=crop&w=480&q=80',
  },
  {
    id: 'lingyin-photo',
    x: 86,
    y: 17,
    width: 148,
    rotate: -1,
    title: '灵隐寺',
    caption: 'Day 2 上午候选',
    src: 'https://images.unsplash.com/photo-1545569341-9eb8b30979d9?auto=format&fit=crop&w=480&q=80',
  },
  {
    id: 'tea-photo',
    x: 17,
    y: 58,
    width: 150,
    rotate: -1,
    title: '龙井茶田',
    caption: '自然风景补充',
    src: 'https://images.unsplash.com/photo-1523920290228-4f321a939b4c?auto=format&fit=crop&w=480&q=80',
  },
  {
    id: 'food-photo',
    x: 86,
    y: 50,
    width: 150,
    rotate: 1,
    title: '东坡肉',
    caption: '晚餐素材',
    src: 'https://images.unsplash.com/photo-1543352634-a1c51d9f1fa7?auto=format&fit=crop&w=480&q=80',
  },
] satisfies ImageItem[]

const itinerary = [
  { day: 'Day 1', focus: '抵达 + 西湖轻量适应', plan: '入住黄龙/武林门，曲院风荷到苏堤，晚餐杭帮菜。' },
  { day: 'Day 2', focus: '自然风景主线', plan: '灵隐或九溪二选一，下午龙井茶田，傍晚回市区。' },
  { day: 'Day 3', focus: '良渚 + 返程缓冲', plan: '良渚文化村，午后小吃补充，预留返程时间。' },
]

const mapTiles = [
  'https://tile.openstreetmap.org/12/3414/1685.png',
  'https://tile.openstreetmap.org/12/3415/1685.png',
  'https://tile.openstreetmap.org/12/3416/1685.png',
  'https://tile.openstreetmap.org/12/3414/1686.png',
  'https://tile.openstreetmap.org/12/3415/1686.png',
  'https://tile.openstreetmap.org/12/3416/1686.png',
]

function itemStyle(item: BoardItem | ImageItem) {
  return {
    position: 'absolute',
    left: `${item.x}%`,
    top: `${item.y}%`,
    width: item.width,
    transform: `translate(-50%, -50%) rotate(${item.rotate ?? 0}deg)`,
  } as CSSProperties
}

function messageBubbleStyle(role: string) {
  return role === 'user'
    ? ({ background: '#2f5f9f', color: '#ffffff' } as CSSProperties)
    : ({ background: '#ffffff', color: '#172033', border: '1px solid #dfe4ea' } as CSSProperties)
}

export function DemoWorkspace({ onOpenSidebar }: DemoWorkspaceProps) {
  return (
    <section className="grid h-full min-h-0 min-w-0 bg-white">
      <div className="grid min-h-0 overflow-hidden" style={{ gridTemplateColumns: 'minmax(330px, 2fr) minmax(0, 3fr)' }}>
        <section className="flex min-h-0 flex-col border-r border-[#d7dbe0] bg-white">
          <div className="flex items-center gap-3 border-b border-[#d7dbe0] px-4 py-3">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-[#eef2f7]">
              <MessageSquareText className="size-5 text-[#38506b]" aria-hidden="true" />
            </span>
            <p className="text-base font-semibold">Agent 交互</p>
            <Button type="button" variant="outline" size="icon" aria-label="Open conversations" onClick={onOpenSidebar} className="ml-auto bg-white">
              <Menu className="size-5" aria-hidden="true" />
            </Button>
          </div>

          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto bg-[#f8fafc] p-4">
            {messages.map((message) => (
              <article
                key={message.id}
                className={message.role === 'user' ? 'ml-auto' : ''}
                style={{ maxWidth: '66%', width: 'fit-content' }}
              >
                <div
                  className="whitespace-pre-wrap break-words rounded-md px-4 py-3 text-sm leading-6 shadow-sm"
                  style={messageBubbleStyle(message.role)}
                >
                  {message.content}
                </div>
                <p className={`mt-1 text-xs ${message.role === 'user' ? 'text-right text-[#7d8a99]' : 'text-[#7d8a99]'}`}>{message.time}</p>
              </article>
            ))}

            <div className="rounded-md border border-[#dfe4ea] bg-white p-3 shadow-sm" style={{ maxWidth: '66%' }}>
              <p className="text-xs font-semibold text-[#38506b]">可以继续这样调整</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {quickActions.map((action) => (
                  <button key={action} type="button" className="rounded-md border border-[#cbd5e1] bg-[#f8fafc] px-2.5 py-1.5 text-xs text-[#38506b]">
                    {action}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <form className="border-t border-[#d7dbe0] bg-white p-4">
            <div className="border border-[#c7d0da] bg-[#fbfcfd] px-3 py-2 shadow-sm" style={{ borderRadius: 18 }}>
              <div className="flex items-start gap-3">
                <Pencil className="mt-2 size-4 shrink-0 text-[#68788a]" aria-hidden="true" />
                <textarea
                  className="max-h-20 min-h-10 min-w-0 flex-1 resize-none bg-transparent text-sm leading-6 outline-none placeholder:text-[#8a96a3]"
                  placeholder="补充偏好，或让 Agent 调整右侧画板..."
                  rows={2}
                />
                <Button type="button" size="icon" aria-label="Send demo prompt" style={{ background: '#2f5f9f', color: '#ffffff', borderRadius: 14 }}>
                  <Send className="size-4" aria-hidden="true" />
                </Button>
              </div>
              <div className="mt-1 flex gap-2 pl-7 text-xs text-[#7d8a99]">
                <span>保留</span>
                <span>替换</span>
                <span>新增素材</span>
              </div>
            </div>
          </form>
        </section>

        <section className="flex min-h-0 flex-col overflow-hidden bg-white">
          <div className="flex items-center justify-between gap-4 border-b border-[#d7dbe0] px-4 py-3">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-[#eef2f7]">
                <Map className="size-5 text-[#38506b]" aria-hidden="true" />
              </span>
              <p className="text-base font-semibold">计划画板</p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Button type="button" variant="outline" size="sm">
                <Plus className="size-4" aria-hidden="true" />
                Note
              </Button>
              <Button type="button" size="sm" style={{ background: '#2f5f9f', color: '#ffffff' }}>
                <Sparkles className="size-4" aria-hidden="true" />
                Arrange
              </Button>
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-hidden bg-[#e8ebef]">
            <div
              className="h-full min-h-[430px] w-full"
              style={{
                position: 'relative',
                backgroundImage: 'radial-gradient(circle, rgba(73, 84, 99, 0.18) 1px, transparent 1px)',
                backgroundSize: '22px 22px',
              }}
            >
              <div
                className="overflow-hidden rounded-md border border-[#b8c3cf] bg-[#cfd8df] shadow-md"
                style={{
                  position: 'absolute',
                  left: '52%',
                  top: '51%',
                  height: 290,
                  width: 'min(560px, 72%)',
                  transform: 'translate(-50%, -50%)',
                }}
              >
                <div
                  aria-label="Hangzhou map preview"
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gridTemplateRows: 'repeat(2, 1fr)',
                    height: '100%',
                    width: '100%',
                  }}
                >
                  {mapTiles.map((tile) => (
                    <div
                      key={tile}
                      style={{
                        backgroundColor: '#d9e3eb',
                        backgroundImage: `url("${tile}")`,
                        backgroundPosition: 'center',
                        backgroundSize: 'cover',
                      }}
                    />
                  ))}
                </div>
                <svg style={{ position: 'absolute', inset: 0, height: '100%', width: '100%' }} viewBox="0 0 560 290" preserveAspectRatio="none" aria-hidden="true">
                  <path d="M 90 190 C 175 150 250 148 320 175 S 455 175 500 126" fill="none" stroke="#2156bd" strokeLinecap="round" strokeWidth="6" />
                  <path d="M 90 190 C 175 150 250 148 320 175 S 455 175 500 126" fill="none" stroke="#ffffff" strokeDasharray="2 12" strokeLinecap="round" strokeWidth="2" />
                </svg>
                {Object.values(mapAnchors).map((anchor) => (
                  <span
                    key={anchor.label}
                    className="rounded-md bg-white/90 px-2 py-1 text-xs font-semibold shadow-sm"
                    style={{ position: 'absolute', left: `${anchor.x}%`, top: `${anchor.y}%`, transform: 'translate(-50%, -50%)' }}
                  >
                    {anchor.label}
                  </span>
                ))}
              </div>

              {boardItems.map((card) => (
                <article key={card.id} className="whitespace-pre-line rounded-md border border-[#d6dce3] p-3 text-sm leading-6 shadow-md" style={{ ...itemStyle(card), background: card.tone }}>
                  <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-[#2f5f9f]">
                    <StickyNote className="size-4" aria-hidden="true" />
                    {card.title}
                  </div>
                  <p>{card.body}</p>
                </article>
              ))}

              {imageItems.map((card) => (
                <article key={card.id} className="overflow-hidden rounded-md border border-[#d6dce3] bg-white shadow-md" style={itemStyle(card)}>
                  <div
                    role="img"
                    aria-label={card.title}
                    style={{
                      height: 80,
                      width: '100%',
                      backgroundColor: '#dbe5ef',
                      backgroundImage: `linear-gradient(135deg, rgba(47,95,159,0.18), rgba(255,255,255,0.05)), url("${card.src}")`,
                      backgroundPosition: 'center',
                      backgroundSize: 'cover',
                    }}
                  />
                  <div className="p-2.5">
                    <p className="text-sm font-semibold">{card.title}</p>
                    <p className="mt-1 text-xs text-[#68788a]">{card.caption}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="border-t border-[#d7dbe0] bg-white px-5 py-4">
            <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
              <Clock3 className="size-4 text-[#38506b]" aria-hidden="true" />
              日程时间轴
            </div>
            <div className="relative grid gap-0 pb-1" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' }}>
              <span aria-hidden="true" style={{ position: 'absolute', left: '7%', right: '7%', top: 11, height: 2, background: '#c8d3df' }} />
              {itinerary.map((item, index) => (
                <article key={item.day} className="relative min-w-0 px-3">
                  <div className="relative flex flex-col items-start">
                    <span className="mb-3 flex size-6 shrink-0 items-center justify-center rounded-full bg-[#2f5f9f] text-xs font-semibold text-white ring-4 ring-white">
                      {index + 1}
                    </span>
                    <p className="text-xs font-semibold text-[#2f5f9f]">{item.day}</p>
                    <p className="mt-1 truncate text-sm font-semibold">{item.focus}</p>
                    <p className="mt-1 text-xs leading-5 text-[#68788a]">{item.plan}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>
      </div>
    </section>
  )
}
