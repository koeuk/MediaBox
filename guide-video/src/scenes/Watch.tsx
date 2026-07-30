import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT, T} from '../theme';
import {AppWindow, Caption, Cursor, Headline, Navbar, Scene} from '../ui';

const NEXT_AT = 200; // click NEXT

const STRIP = [
  {label: 'How To Become Da…', grad: 'linear-gradient(135deg,#3a2d1f,#6b5133)'},
  {label: 'MCP vs API Explaine…', grad: 'linear-gradient(135deg,#12303a,#1f5c68)'},
  {label: 'System Design Expla…', grad: 'linear-gradient(135deg,#1c2a1c,#3d5c3d)'},
  {label: 'TikTok video #76641…', grad: 'linear-gradient(135deg,#5d2a42,#b06161)'},
  {label: 'Mortals (Slowed) #he…', grad: 'linear-gradient(135deg,#22222c,#44445c)'},
  {label: 'របៀបក្នុងការនិយាយឲ្យ…', grad: 'linear-gradient(135deg,#2d2438,#5c4a73)'},
];

export const Watch: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const dialogIn = spring({frame: frame - 24, fps, config: {damping: 200}});
  const advanced = frame >= NEXT_AT + 6;
  const playingIdx = advanced ? 4 : 3;
  const counter = advanced ? 9 : 8;
  const swap = spring({frame: frame - (NEXT_AT + 6), fps, config: {damping: 200}});

  return (
    <Scene>
      <Headline
        kicker="02 · Watch"
        title="Click a card. Just watch."
        sub="Built-in player · auto-next slideshow · minimize to a floating mini-player"
      />
      <AppWindow delay={8}>
        <Navbar />
        {/* dimmed listing behind the dialog */}
        <div style={{position: 'absolute', inset: 0, top: 64, background: 'rgba(0,0,0,0.55)'}} />

        {/* preview dialog */}
        <div
          style={{
            position: 'absolute',
            left: 250,
            top: 78,
            width: 1020,
            opacity: dialogIn,
            transform: `translateY(${interpolate(dialogIn, [0, 1], [40, 0])}px)`,
            background: T.bgRaised,
            border: `1px solid ${T.lineStrong}`,
            borderRadius: 14,
            boxShadow: '0 10px 30px rgba(0,0,0,0.45)',
            overflow: 'hidden',
          }}
        >
          {/* title bar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 22,
              padding: '14px 22px',
              borderBottom: `1px solid ${T.line}`,
            }}
          >
            <div style={{flex: 1, fontFamily: FONT.display, fontWeight: 600, fontSize: 19, color: T.text}}>
              {advanced ? 'Mortals (Slowed) #headphones' : 'TikTok video #7664110060070587669'}
            </div>
            <div style={{fontSize: 18, color: T.dim}}>⤢</div>
            <div
              style={{
                fontFamily: FONT.mono,
                fontSize: 15,
                letterSpacing: '0.12em',
                color: T.dim,
              }}
            >
              SAVE
            </div>
            <div style={{fontSize: 18, color: T.dim}}>✕</div>
          </div>

          {/* player */}
          <div
            style={{
              height: 290,
              background: '#000',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div
              style={{
                width: 200,
                height: 264,
                borderRadius: 4,
                background: advanced
                  ? 'linear-gradient(160deg,#22222c 0%,#44445c 70%,#5c5c7a 100%)'
                  : 'linear-gradient(160deg,#5d2a42 0%,#8d4a5c 60%,#b06161 100%)',
                opacity: advanced ? swap : 1,
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              {/* fake playback shimmer */}
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  background:
                    'linear-gradient(115deg, transparent 30%, rgba(255,255,255,0.08) 50%, transparent 70%)',
                  transform: `translateX(${interpolate(frame % 90, [0, 90], [-200, 200])}px)`,
                }}
              />
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  right: 0,
                  bottom: 0,
                  height: 4,
                  background: 'rgba(255,255,255,0.2)',
                }}
              >
                <div
                  style={{
                    width: `${interpolate(frame, [30, 330], [5, 92], {
                      extrapolateLeft: 'clamp',
                      extrapolateRight: 'clamp',
                    })}%`,
                    height: '100%',
                    background: T.accent,
                  }}
                />
              </div>
            </div>
          </div>

          {/* controls */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 26,
              padding: '13px 22px',
            }}
          >
            <div
              style={{
                fontFamily: FONT.mono,
                fontSize: 15,
                letterSpacing: '0.12em',
                color: T.dim,
                border: `1px solid ${T.lineStrong}`,
                borderRadius: 8,
                padding: '9px 18px',
              }}
            >
              ‹ BACK
            </div>
            <div
              style={{
                fontFamily: FONT.mono,
                fontSize: 15,
                color: T.text,
                border: `1px solid ${T.line}`,
                borderRadius: 8,
                padding: '9px 16px',
              }}
            >
              {counter} / 58
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 9,
                background: T.accentSoft,
                border: `1px solid ${T.accent}55`,
                borderRadius: 999,
                padding: '7px 15px',
              }}
            >
              <div style={{width: 30, height: 16, borderRadius: 8, background: T.accent, position: 'relative'}}>
                <div
                  style={{
                    position: 'absolute',
                    right: 2,
                    top: 2,
                    width: 12,
                    height: 12,
                    borderRadius: 6,
                    background: T.accentInk,
                  }}
                />
              </div>
              <span style={{fontFamily: FONT.display, fontSize: 15, color: T.text}}>Auto next</span>
            </div>
            <div
              style={{
                fontFamily: FONT.mono,
                fontSize: 15,
                letterSpacing: '0.12em',
                color: frame >= NEXT_AT && frame <= NEXT_AT + 6 ? T.accentInk : T.dim,
                background: frame >= NEXT_AT && frame <= NEXT_AT + 6 ? T.accent : 'transparent',
                border: `1px solid ${T.lineStrong}`,
                borderRadius: 8,
                padding: '9px 18px',
              }}
            >
              NEXT ›
            </div>
          </div>

          {/* filmstrip */}
          <div
            style={{
              display: 'flex',
              gap: 12,
              justifyContent: 'center',
              padding: '4px 22px 18px',
            }}
          >
            {STRIP.map((tile, i) => {
              const playing = i === playingIdx;
              return (
                <div
                  key={tile.label}
                  style={{
                    width: 148,
                    height: 100,
                    borderRadius: 10,
                    background: tile.grad,
                    border: `2px solid ${playing ? T.accent : T.line}`,
                    position: 'relative',
                    overflow: 'hidden',
                    opacity: playing ? 1 : 0.75,
                  }}
                >
                  {playing ? (
                    <div
                      style={{
                        position: 'absolute',
                        top: 8,
                        right: 8,
                        fontFamily: FONT.mono,
                        fontSize: 11,
                        letterSpacing: '0.1em',
                        color: T.accentInk,
                        background: T.accent,
                        borderRadius: 5,
                        padding: '3px 7px',
                      }}
                    >
                      PLAYING
                    </div>
                  ) : null}
                  <div
                    style={{
                      position: 'absolute',
                      left: 0,
                      right: 0,
                      bottom: 0,
                      fontFamily: FONT.display,
                      fontSize: 12,
                      color: '#fff',
                      background: 'rgba(10,11,13,0.7)',
                      padding: '5px 8px',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {tile.label}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <Cursor
          path={[
            {f: 120, x: 800, y: 420},
            {f: NEXT_AT - 4, x: 940, y: 452},
            {f: 260, x: 900, y: 500},
          ]}
          clicks={[NEXT_AT]}
        />
      </AppWindow>
      <Caption text="Auto next plays through your box — minimize keeps it playing in a corner" delay={190} />
    </Scene>
  );
};
