import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {AppWindow, Caption, CategoryPills, Cursor, Headline, MediaCard, Navbar, Scene, StatusTabs} from '../ui';

type Item = {title: string; meta: string; cat: string; grad: string};

const ITEMS: Item[] = [
  {title: 'Learn 97% of Claude in Under 16 …', meta: '294.4 MB · video/mp4', cat: 'AI', grad: 'linear-gradient(135deg,#1f3a5f,#4a7a96)'},
  {title: 'MCP vs API Explained: Do You R…', meta: '136.9 MB · video/mp4', cat: 'CODING', grad: 'linear-gradient(135deg,#12303a,#1f5c68)'},
  {title: 'System Design Explained: APIs, …', meta: '210.5 MB · video/mp4', cat: 'CODING', grad: 'linear-gradient(135deg,#1c2a1c,#3d5c3d)'},
  {title: 'Bye _ Bye — Ariana Grande @JD …', meta: '2.6 MB · video/mp4', cat: 'FUN', grad: 'linear-gradient(135deg,#4a3a10,#a08020)'},
  {title: 'Advance English Learning | Collo…', meta: '306.0 MB · video/mp4', cat: 'TOP', grad: 'linear-gradient(135deg,#2d4a3e,#5c8d76)'},
  {title: 'Software Engineering 101', meta: '188.1 MB · video/mp4', cat: 'CODING', grad: 'linear-gradient(135deg,#233242,#3f5c73)'},
  {title: 'TikTok video #7664110060070587…', meta: '18.2 MB · video/mp4', cat: 'FUN', grad: 'linear-gradient(135deg,#5d2a42,#b06161)'},
  {title: 'How To Become Dangerously Se…', meta: '154.7 MB · video/mp4', cat: 'TOP', grad: 'linear-gradient(135deg,#3a2d1f,#6b5133)'},
];

const FILTER_AT = 130; // click on the CODING pill
const FAV_AT = 255; // click star on the first coding card

export const Organize: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const filtered = frame >= FILTER_AT + 8;
  const currentCat = filtered ? 'CODING' : 'ALL';
  const fav = frame >= FAV_AT + 4;
  const favPop = spring({frame: frame - (FAV_AT + 4), fps, config: {damping: 10, mass: 0.6}});

  const visible = ITEMS.filter((i) => !filtered || i.cat === 'CODING');

  return (
    <Scene>
      <Headline
        kicker="03 · Organize"
        title="Your box, your order."
        sub="Status tabs · category pills · favorites · hidden — all one click away"
      />
      <AppWindow delay={8}>
        <Navbar />
        <div style={{padding: '20px 30px 0'}}>
          <div style={{display: 'flex', alignItems: 'center', gap: 24}}>
            <StatusTabs counts={{all: 59, favorites: fav ? 4 : 3, active: 0, failed: 0}} />
            <CategoryPills cats={['ALL', 'TOP', 'FUN', 'CODING', 'AI', 'FRESH', 'VIEW']} current={currentCat} />
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 18,
              marginTop: 20,
            }}
          >
            {ITEMS.map((item, i) => {
              const shown = visible.includes(item);
              const inSpring = spring({frame: frame - 16 - i * 4, fps, config: {damping: 200}});
              const hide = filtered && !shown;
              const hideT = spring({frame: frame - (FILTER_AT + 8), fps, config: {damping: 200}});
              if (hide && hideT > 0.98) return null;
              const isFavTarget = item.title.startsWith('MCP vs API');
              return (
                <div
                  key={item.title}
                  style={{
                    opacity: inSpring * (hide ? 1 - hideT : 1),
                    transform: `scale(${hide ? interpolate(hideT, [0, 1], [1, 0.85]) : 1}) translateY(${interpolate(inSpring, [0, 1], [24, 0])}px)`,
                  }}
                >
                  <MediaCard
                    title={item.title}
                    meta={item.meta}
                    grad={item.grad}
                    compact
                    fav={isFavTarget && fav}
                    favPop={favPop}
                  />
                </div>
              );
            })}
          </div>
        </div>

        <Cursor
          path={[
            {f: 85, x: 900, y: 420},
            {f: FILTER_AT - 4, x: 962, y: 116},
            {f: 210, x: 500, y: 260},
            {f: FAV_AT - 4, x: 382, y: 172},
            {f: 300, x: 520, y: 330},
          ]}
          clicks={[FILTER_AT, FAV_AT]}
        />
      </AppWindow>
      <Caption text="Rename, recolor & reorder categories — changes cascade to your media" delay={200} />
    </Scene>
  );
};
