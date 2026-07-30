import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT, T} from '../theme';
import {ActionBtn, AppWindow, Caption, Chip, Cursor, Headline, Navbar, ProgressBar, Scene} from '../ui';

const MENU_AT = 60; // click CONVERT ▾
const PICK_AT = 140; // click "gif"
const FORMATS = ['mp4', 'webm', 'gif', 'mp3', 'm4a', 'wav'];

export const Convert: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const menuOpen = frame >= MENU_AT + 4 && frame < PICK_AT + 6;
  const menuS = spring({frame: frame - (MENU_AT + 4), fps, config: {damping: 200}});
  const pct = interpolate(frame, [PICK_AT + 15, 265], [0, 100], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const converting = frame >= PICK_AT + 10 && frame < 268;
  const done = frame >= 268;
  const doneS = spring({frame: frame - 268, fps, config: {damping: 200}});

  return (
    <Scene>
      <Headline
        kicker="04 · Convert"
        title="Any format, via FFmpeg."
        sub="mp4 · webm · gif · mp3 · m4a · wav — progress tracked in real time"
      />
      <AppWindow delay={8}>
        <Navbar />
        <div style={{display: 'flex', gap: 26, padding: '30px 30px'}}>
          {/* source card */}
          <div
            style={{
              flex: 1,
              padding: 26,
              background: T.surface,
              border: `1px solid ${T.line}`,
              borderRadius: 14,
              position: 'relative',
            }}
          >
            <div style={{display: 'flex', gap: 24}}>
              <div
                style={{
                  width: 220,
                  height: 124,
                  borderRadius: 10,
                  background: 'linear-gradient(135deg,#12303a,#1f5c68)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: FONT.mono,
                  fontSize: 17,
                  color: '#ffffffcc',
                }}
              >
                ▶ 12:36
              </div>
              <div style={{flex: 1}}>
                <div style={{fontFamily: FONT.display, fontWeight: 700, fontSize: 24, color: T.text}}>
                  MCP vs API Explained: Do You Really…
                </div>
                <div style={{fontFamily: FONT.mono, fontSize: 16, color: T.faint, marginTop: 8}}>
                  136.9 MB · video/mp4
                </div>
                <div style={{display: 'flex', gap: 10, marginTop: 16}}>
                  <ActionBtn label="Convert" caret highlight={menuOpen} />
                  <ActionBtn label="Tag" caret />
                  <ActionBtn label="⋮" />
                </div>
              </div>
            </div>

            {converting || done ? (
              <div style={{marginTop: 24}}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontFamily: FONT.mono,
                    fontSize: 17,
                    color: done ? T.ok : T.accent,
                    marginBottom: 10,
                  }}
                >
                  <span>{done ? '✓ converted → gif' : `converting → gif · ${Math.round(pct)}%`}</span>
                  {!done && (
                    <span style={{color: T.faint}}>
                      frame={Math.round(pct * 68)} fps=96 time=00:00:
                      {String(Math.round(pct * 0.27)).padStart(2, '0')}
                    </span>
                  )}
                </div>
                <ProgressBar pct={pct} color={done ? T.ok : T.accent} />
              </div>
            ) : null}

            {/* convert dropdown under the CONVERT button */}
            {menuOpen ? (
              <div
                style={{
                  position: 'absolute',
                  top: 178,
                  left: 270,
                  width: 230,
                  background: T.bgRaised,
                  border: `1px solid ${T.lineStrong}`,
                  borderRadius: 12,
                  boxShadow: '0 10px 30px rgba(0,0,0,0.45)',
                  padding: 9,
                  opacity: menuS,
                  transform: `translateY(${interpolate(menuS, [0, 1], [-12, 0])}px)`,
                  zIndex: 30,
                }}
              >
                <div
                  style={{
                    fontFamily: FONT.mono,
                    fontSize: 13,
                    textTransform: 'uppercase',
                    letterSpacing: '0.14em',
                    color: T.faint,
                    padding: '7px 13px',
                  }}
                >
                  Convert to
                </div>
                {FORMATS.map((f) => (
                  <div
                    key={f}
                    style={{
                      fontFamily: FONT.mono,
                      fontSize: 18,
                      color: f === 'gif' && frame >= PICK_AT - 12 ? T.accentInk : T.text,
                      background: f === 'gif' && frame >= PICK_AT - 12 ? T.accent : 'transparent',
                      borderRadius: 8,
                      padding: '8px 13px',
                    }}
                  >
                    {f}
                  </div>
                ))}
              </div>
            ) : null}
          </div>

          {/* derived card appears when done */}
          <div
            style={{
              width: 330,
              padding: 24,
              background: T.surface,
              border: `1px solid ${T.ok}55`,
              borderRadius: 14,
              opacity: doneS,
              transform: `translateX(${interpolate(doneS, [0, 1], [40, 0])}px)`,
              alignSelf: 'flex-start',
            }}
          >
            <div
              style={{
                height: 112,
                borderRadius: 10,
                background: 'linear-gradient(135deg,#1f5c68,#12303a)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontFamily: FONT.mono,
                fontSize: 17,
                color: '#ffffffcc',
                marginBottom: 16,
              }}
            >
              GIF · 8.1 MB
            </div>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
              <div style={{fontFamily: FONT.display, fontWeight: 700, fontSize: 18, color: T.text}}>
                MCP vs API.gif
              </div>
              <Chip label="done" color={T.ok} soft={T.okSoft} size={14} />
            </div>
          </div>
        </div>

        <Cursor
          path={[
            {f: 25, x: 700, y: 400},
            {f: MENU_AT - 4, x: 365, y: 200},
            {f: 100, x: 390, y: 280},
            {f: PICK_AT - 4, x: 385, y: 330},
            {f: 190, x: 700, y: 430},
          ]}
          clicks={[MENU_AT, PICK_AT]}
        />
      </AppWindow>
      <Caption text="Conversions keep the original — derived files show up as their own cards" delay={180} />
    </Scene>
  );
};
