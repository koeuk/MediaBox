import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT, T} from '../theme';
import {
  ActionBtn,
  AppWindow,
  Caption,
  CategoryPills,
  Cursor,
  Headline,
  MediaCard,
  Navbar,
  Scene,
  StatusTabs,
  useTypewriter,
} from '../ui';

const URL_TEXT = 'https://www.tiktok.com/@nature/video/7664110060070587669';
const CLICK_AT = 122;
const CARD_AT = 132;
const DL_START = 150;
const DL_END = 330;
const DONE_AT = 335;

const EXISTING = [
  {title: 'Learn 97% of Claude in Under 16 …', meta: '294.4 MB · video/mp4', grad: 'linear-gradient(135deg,#1f3a5f,#4a7a96)'},
  {title: 'Bye _ Bye — Ariana Grande @JD …', meta: '2.6 MB · video/mp4', grad: 'linear-gradient(135deg,#4a3a10,#a08020)'},
  {title: 'MCP vs API Explained: Do You R…', meta: '136.9 MB · video/mp4', grad: 'linear-gradient(135deg,#12303a,#1f5c68)'},
];

export const Download: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const url = useTypewriter(URL_TEXT, 40, 105);
  const cardIn = spring({frame: frame - CARD_AT, fps, config: {damping: 200}});
  const pct = interpolate(frame, [DL_START, DL_END], [0, 100], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const done = frame >= DONE_AT;
  const downloading = frame >= CARD_AT && !done;
  const mb = (pct / 100) * 18.2;

  return (
    <Scene>
      <Headline
        kicker="01 · Download"
        title="Add to your box."
        sub="TikTok · Facebook · direct media URLs — pick a quality, or upload your own"
      />
      <AppWindow delay={8}>
        <Navbar />
        <div style={{padding: '22px 30px 0'}}>
          <div
            style={{
              fontFamily: FONT.display,
              fontWeight: 800,
              fontSize: 38,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: T.text,
              marginBottom: 16,
            }}
          >
            Add to your box
          </div>

          {/* submit row */}
          <div style={{display: 'flex', gap: 14}}>
            <div
              style={{
                flex: 1,
                height: 54,
                display: 'flex',
                alignItems: 'center',
                padding: '0 20px',
                fontFamily: FONT.mono,
                fontSize: 18,
                color: url ? T.text : T.faint,
                background: T.surface,
                border: `1px solid ${frame >= 30 && frame <= 110 ? T.accent : T.line}`,
                borderRadius: 10,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
              }}
            >
              {url || 'https:// — paste direct media URLs or TikTok/Facebook video links'}
              {frame >= 30 && frame <= 110 ? (
                <span style={{color: T.accent, opacity: frame % 16 < 8 ? 1 : 0}}>▍</span>
              ) : null}
            </div>
            <div
              style={{
                height: 54,
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '0 20px',
                fontFamily: FONT.display,
                fontWeight: 600,
                fontSize: 19,
                color: T.dim,
                background: T.surface,
                border: `1px solid ${T.line}`,
                borderRadius: 10,
              }}
            >
              Best <span style={{fontSize: 13}}>▾</span>
            </div>
            <div
              style={{
                height: 54,
                display: 'flex',
                alignItems: 'center',
                padding: '0 30px',
                fontFamily: FONT.display,
                fontWeight: 800,
                fontSize: 19,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                color: T.accentInk,
                background: frame >= CLICK_AT && frame <= CLICK_AT + 6 ? T.accentStrong : T.accent,
                borderRadius: 10,
              }}
            >
              Download
            </div>
            <div
              style={{
                height: 54,
                display: 'flex',
                alignItems: 'center',
                padding: '0 26px',
                fontFamily: FONT.display,
                fontWeight: 700,
                fontSize: 19,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                color: T.text,
                background: 'transparent',
                border: `1px solid ${T.lineStrong}`,
                borderRadius: 10,
              }}
            >
              Upload
            </div>
          </div>

          {/* status tabs + category pills */}
          <div style={{display: 'flex', alignItems: 'center', gap: 24, marginTop: 18}}>
            <StatusTabs
              counts={{
                all: done || downloading ? 59 : 58,
                favorites: 3,
                active: downloading ? 1 : 0,
                failed: 0,
              }}
            />
            <CategoryPills cats={['ALL', 'TOP', 'FUN', 'CODING', 'AI', 'FRESH']} />
          </div>

          {/* card grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 18,
              marginTop: 20,
            }}
          >
            <div
              style={{
                opacity: cardIn,
                transform: `translateY(${interpolate(cardIn, [0, 1], [26, 0])}px)`,
              }}
            >
              <MediaCard
                title="TikTok video #7664110060070587669"
                meta={
                  done
                    ? '18.2 MB · video/mp4'
                    : downloading
                      ? `${mb.toFixed(1)} MB / 18.2 MB · 4.2 MB/s`
                      : 'queued…'
                }
                grad="linear-gradient(135deg,#5d2a42,#b06161)"
                status={done ? 'completed' : 'downloading'}
                progress={pct}
                actions={done}
              />
            </div>
            {EXISTING.map((c) => (
              <MediaCard key={c.title} title={c.title} meta={c.meta} grad={c.grad} actions />
            ))}
          </div>
        </div>

        <Cursor
          path={[
            {f: 85, x: 880, y: 420},
            {f: CLICK_AT - 4, x: 1258, y: 200},
            {f: 155, x: 1100, y: 330},
          ]}
          clicks={[CLICK_AT]}
        />
      </AppWindow>
      <Caption text="Live progress streams over WebSocket — batch links & uploads supported" delay={170} />
    </Scene>
  );
};
