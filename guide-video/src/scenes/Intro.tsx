import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT, T} from '../theme';
import {Scene, useTypewriter} from '../ui';

export const Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const mark = spring({frame, fps, config: {damping: 14, mass: 0.8}});
  const title = spring({frame: frame - 14, fps, config: {damping: 200}});
  const spacing = interpolate(title, [0, 1], [0.4, 0.06]);
  const tagline = useTypewriter('Download, Organize, and Manage Your Media', 62, 118);

  return (
    <Scene>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div
          style={{
            width: 130,
            height: 130,
            borderRadius: 34,
            background: T.accent,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transform: `scale(${mark})`,
            boxShadow: `0 0 90px ${T.accent}55`,
          }}
        >
          <div
            style={{
              width: 0,
              height: 0,
              borderTop: '26px solid transparent',
              borderBottom: '26px solid transparent',
              borderLeft: `42px solid ${T.accentInk}`,
              marginLeft: 10,
            }}
          />
        </div>
        <div
          style={{
            marginTop: 52,
            fontFamily: FONT.display,
            fontWeight: 800,
            fontSize: 128,
            textTransform: 'uppercase',
            letterSpacing: `${spacing}em`,
            color: T.text,
            opacity: title,
          }}
        >
          MediaBox
        </div>
        <div
          style={{
            marginTop: 30,
            height: 40,
            fontFamily: FONT.mono,
            fontSize: 30,
            letterSpacing: '0.08em',
            color: T.dim,
          }}
        >
          {tagline}
          <span style={{color: T.accent, opacity: frame % 20 < 10 ? 1 : 0}}>▍</span>
        </div>
      </AbsoluteFill>
    </Scene>
  );
};
