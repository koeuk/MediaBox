import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT, T} from '../theme';
import {Scene} from '../ui';

const FEATURES = [
  'Live progress over WebSocket',
  'Built-in player with auto-next',
  'Batch downloads, retries & resume',
  'Favorites, hidden & color-coded categories',
  'FFmpeg conversion to any format',
];

const SWITCH_AT = 150;
const STACK = ['FastAPI', 'Nuxt 4', 'MySQL', 'FFmpeg', 'Docker'];

export const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const listOpacity = interpolate(frame, [SWITCH_AT - 14, SWITCH_AT], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const endS = spring({frame: frame - SWITCH_AT, fps, config: {damping: 200}});

  return (
    <Scene>
      {/* feature recap */}
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', opacity: listOpacity}}>
        <div>
          <div
            style={{
              fontFamily: FONT.mono,
              fontSize: 26,
              textTransform: 'uppercase',
              letterSpacing: '0.22em',
              color: T.accent,
              marginBottom: 36,
            }}
          >
            Everything included
          </div>
          {FEATURES.map((feat, i) => {
            const s = spring({frame: frame - 10 - i * 12, fps, config: {damping: 200}});
            return (
              <div
                key={feat}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 22,
                  marginBottom: 24,
                  opacity: s,
                  transform: `translateX(${interpolate(s, [0, 1], [40, 0])}px)`,
                }}
              >
                <div
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: 17,
                    background: T.okSoft,
                    border: `1px solid ${T.ok}66`,
                    color: T.ok,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontFamily: FONT.mono,
                    fontSize: 18,
                  }}
                >
                  ✓
                </div>
                <div style={{fontFamily: FONT.display, fontWeight: 800, fontSize: 36, color: T.text}}>
                  {feat}
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>

      {/* end card */}
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', opacity: endS}}>
        <div
          style={{
            width: 110,
            height: 110,
            borderRadius: 28,
            background: T.accent,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 0 90px ${T.accent}55`,
            transform: `scale(${endS})`,
          }}
        >
          <div
            style={{
              width: 0,
              height: 0,
              borderTop: '22px solid transparent',
              borderBottom: '22px solid transparent',
              borderLeft: `36px solid ${T.accentInk}`,
              marginLeft: 8,
            }}
          />
        </div>
        <div
          style={{
            marginTop: 44,
            fontFamily: FONT.display,
            fontWeight: 800,
            fontSize: 100,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: T.text,
          }}
        >
          MediaBox
        </div>
        <div
          style={{
            marginTop: 22,
            fontFamily: FONT.mono,
            fontSize: 32,
            letterSpacing: '0.14em',
            textTransform: 'uppercase',
            color: T.accent,
          }}
        >
          Fast. Secure. Organized.
        </div>
        <div style={{display: 'flex', gap: 16, marginTop: 56}}>
          {STACK.map((tech, i) => {
            const s = spring({frame: frame - SWITCH_AT - 20 - i * 6, fps, config: {damping: 200}});
            return (
              <div
                key={tech}
                style={{
                  fontFamily: FONT.mono,
                  fontSize: 21,
                  color: T.dim,
                  background: T.surface,
                  border: `1px solid ${T.line}`,
                  borderRadius: 999,
                  padding: '10px 26px',
                  opacity: s,
                  transform: `translateY(${interpolate(s, [0, 1], [20, 0])}px)`,
                }}
              >
                {tech}
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </Scene>
  );
};
