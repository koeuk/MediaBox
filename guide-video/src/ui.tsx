import React from 'react';
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {FONT, T} from './theme';

const GRAIN = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3CfeColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.04 0'/%3E%3C/filter%3E%3Crect width='120' height='120' filter='url(%23n)'/%3E%3C/svg%3E")`;

export const Grain: React.FC = () => (
  <div
    style={{
      position: 'absolute',
      inset: 0,
      pointerEvents: 'none',
      zIndex: 50,
      opacity: 0.5,
      backgroundImage: GRAIN,
    }}
  />
);

// Scene wrapper: MediaBox background + fade in/out + film grain.
export const Scene: React.FC<{children: React.ReactNode}> = ({children}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const opacity = interpolate(
    frame,
    [0, 12, durationInFrames - 12, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );
  return (
    <AbsoluteFill style={{backgroundColor: T.bg}}>
      <AbsoluteFill style={{opacity}}>
        {children}
        <Grain />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// Kicker (mono label) + big display title, springing up.
export const Headline: React.FC<{
  kicker: string;
  title: string;
  sub?: string;
  delay?: number;
}> = ({kicker, title, sub, delay = 0}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: frame - delay, fps, config: {damping: 200}});
  const y = interpolate(s, [0, 1], [40, 0]);
  return (
    <div style={{position: 'absolute', top: 84, left: 110, right: 110, opacity: s, transform: `translateY(${y}px)`}}>
      <div
        style={{
          fontFamily: FONT.mono,
          fontSize: 26,
          textTransform: 'uppercase',
          letterSpacing: '0.22em',
          color: T.accent,
          marginBottom: 18,
        }}
      >
        {kicker}
      </div>
      <div
        style={{
          fontFamily: FONT.display,
          fontWeight: 800,
          fontSize: 76,
          textTransform: 'uppercase',
          letterSpacing: '0.02em',
          color: T.text,
          lineHeight: 1.05,
        }}
      >
        {title}
      </div>
      {sub ? (
        <div style={{fontFamily: FONT.mono, fontSize: 26, color: T.dim, marginTop: 20}}>{sub}</div>
      ) : null}
    </div>
  );
};

// Fake browser window holding the app mockup.
export const AppWindow: React.FC<{
  children: React.ReactNode;
  delay?: number;
  width?: number;
  height?: number;
  top?: number;
}> = ({children, delay = 0, width = 1520, height = 660, top = 340}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: frame - delay, fps, config: {damping: 200}});
  const y = interpolate(s, [0, 1], [70, 0]);
  return (
    <div
      style={{
        position: 'absolute',
        top,
        left: (1920 - width) / 2,
        width,
        height,
        opacity: s,
        transform: `translateY(${y}px)`,
        background: T.bg,
        border: `1px solid ${T.line}`,
        borderRadius: 18,
        boxShadow: '0 10px 30px rgba(0,0,0,0.45)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          height: 54,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '0 22px',
          borderBottom: `1px solid ${T.line}`,
          background: T.surface,
        }}
      >
        {['#e5484d', '#f2a33c', '#55c47c'].map((c) => (
          <div key={c} style={{width: 14, height: 14, borderRadius: 7, background: c, opacity: 0.9}} />
        ))}
        <div
          style={{
            marginLeft: 22,
            fontFamily: FONT.mono,
            fontSize: 18,
            color: T.faint,
            background: T.bg,
            border: `1px solid ${T.line}`,
            borderRadius: 9,
            padding: '6px 18px',
          }}
        >
          mediabox.local
        </div>
      </div>
      <div style={{position: 'relative', height: height - 54}}>{children}</div>
    </div>
  );
};

// MEDIA (white) + BOX (amber), like the real navbar logo.
export const Logo: React.FC<{size?: number}> = ({size = 26}) => (
  <div style={{display: 'flex', alignItems: 'center', gap: size * 0.45}}>
    <div
      style={{
        width: size * 1.15,
        height: size * 1.15,
        borderRadius: '50%',
        background: T.accent,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          width: 0,
          height: 0,
          borderTop: `${size * 0.22}px solid transparent`,
          borderBottom: `${size * 0.22}px solid transparent`,
          borderLeft: `${size * 0.36}px solid ${T.accentInk}`,
          marginLeft: size * 0.08,
        }}
      />
    </div>
    <div
      style={{
        fontFamily: FONT.display,
        fontWeight: 800,
        fontSize: size,
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
      }}
    >
      <span style={{color: T.text}}>MEDIA</span>
      <span style={{color: T.accent}}>BOX</span>
    </div>
  </div>
);

const NAV_ITEMS = ['Remove BG', 'Media', 'Categories', 'Admin', 'Settings'];

export const Navbar: React.FC<{active?: string}> = ({active = 'Media'}) => (
  <div
    style={{
      height: 64,
      display: 'flex',
      alignItems: 'center',
      padding: '0 30px',
      gap: 8,
      borderBottom: `1px solid ${T.line}`,
      background: '#0a0b0d',
    }}
  >
    <Logo />
    <div style={{flex: 1}} />
    {NAV_ITEMS.map((item) => {
      const isActive = item === active;
      return (
        <div
          key={item}
          style={{
            fontFamily: FONT.display,
            fontWeight: 500,
            fontSize: 18,
            color: isActive ? T.text : T.dim,
            background: isActive ? T.surfaceHover : 'transparent',
            border: `1px solid ${isActive ? T.lineStrong : 'transparent'}`,
            borderRadius: 9,
            padding: '9px 18px',
          }}
        >
          {item}
        </div>
      );
    })}
    <div style={{fontSize: 19, color: T.dim, marginLeft: 10}}>☀</div>
  </div>
);

// Status tabs row: ALL (n) · FAVORITES (n) · ACTIVE (n) · FAILED (n)
export const StatusTabs: React.FC<{
  counts: {all: number; favorites: number; active: number; failed: number};
  current?: string;
}> = ({counts, current = 'ALL'}) => {
  const tabs: [string, number][] = [
    ['ALL', counts.all],
    ['FAVORITES', counts.favorites],
    ['ACTIVE', counts.active],
    ['FAILED', counts.failed],
  ];
  return (
    <div
      style={{
        display: 'inline-flex',
        gap: 6,
        padding: 6,
        border: `1px solid ${T.line}`,
        borderRadius: 10,
        background: T.surface,
      }}
    >
      {tabs.map(([label, n]) => {
        const isActive = label === current;
        return (
          <div
            key={label}
            style={{
              fontFamily: FONT.mono,
              fontSize: 15,
              letterSpacing: '0.08em',
              color: isActive ? T.accentInk : T.dim,
              background: isActive ? T.accent : 'transparent',
              borderRadius: 7,
              padding: '8px 14px',
            }}
          >
            {label} ({n})
          </div>
        );
      })}
    </div>
  );
};

// Category pills: ALL TOP FUN CODING AI … + LIVE dot
export const CategoryPills: React.FC<{cats: string[]; current?: string}> = ({
  cats,
  current = 'ALL',
}) => (
  <div style={{display: 'inline-flex', alignItems: 'center', gap: 8}}>
    {cats.map((cat) => {
      const isActive = cat === current;
      return (
        <div
          key={cat}
          style={{
            fontFamily: FONT.mono,
            fontSize: 15,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: isActive ? T.accentInk : T.dim,
            background: isActive ? T.accent : 'transparent',
            borderRadius: 7,
            padding: '8px 14px',
          }}
        >
          {cat}
        </div>
      );
    })}
    <div style={{display: 'flex', alignItems: 'center', gap: 7, marginLeft: 8}}>
      <div style={{width: 9, height: 9, borderRadius: 5, background: T.ok}} />
      <span style={{fontFamily: FONT.mono, fontSize: 14, letterSpacing: '0.1em', color: T.dim}}>
        LIVE
      </span>
    </div>
  </div>
);

// Small outline action button: CONVERT ▾ / TAG ▾ / ⋮
export const ActionBtn: React.FC<{label: string; caret?: boolean; highlight?: boolean}> = ({
  label,
  caret,
  highlight,
}) => (
  <div
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 7,
      fontFamily: FONT.mono,
      fontSize: 14,
      letterSpacing: '0.1em',
      textTransform: 'uppercase',
      color: highlight ? T.accentInk : T.dim,
      background: highlight ? T.accent : T.surface,
      border: `1px solid ${highlight ? T.accent : T.lineStrong}`,
      borderRadius: 8,
      padding: '9px 15px',
    }}
  >
    {label}
    {caret ? <span style={{fontSize: 11}}>▾</span> : null}
  </div>
);

// Grid media card matching the real listing UI.
export const MediaCard: React.FC<{
  title: string;
  meta: string;
  grad: string;
  status?: 'completed' | 'downloading';
  fav?: boolean;
  favPop?: number;
  progress?: number;
  actions?: boolean;
  compact?: boolean;
}> = ({title, meta, grad, status = 'completed', fav, favPop = 1, progress, actions, compact}) => {
  const done = status === 'completed';
  return (
    <div
      style={{
        background: T.surface,
        border: `1px solid ${T.line}`,
        borderRadius: 12,
        overflow: 'hidden',
      }}
    >
      <div style={{height: compact ? 118 : 140, background: grad, position: 'relative'}}>
        <div
          style={{
            position: 'absolute',
            top: 10,
            left: 10,
            fontFamily: FONT.mono,
            fontSize: 12,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: done ? T.ok : T.accent,
            background: 'rgba(10,11,13,0.72)',
            borderRadius: 6,
            padding: '5px 9px',
          }}
        >
          {status}
        </div>
        <div
          style={{
            position: 'absolute',
            top: 8,
            right: 10,
            fontSize: 22,
            color: fav ? T.accent : 'rgba(255,255,255,0.75)',
            transform: `scale(${fav ? interpolate(favPop, [0, 1], [1.7, 1]) : 1})`,
            textShadow: '0 1px 4px rgba(0,0,0,0.6)',
          }}
        >
          {fav ? '★' : '☆'}
        </div>
        {progress !== undefined && !done ? (
          <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 6, background: 'rgba(0,0,0,0.5)'}}>
            <div style={{width: `${progress}%`, height: '100%', background: T.accent}} />
          </div>
        ) : null}
      </div>
      <div style={{padding: compact ? '10px 13px 12px' : '12px 15px 14px'}}>
        <div
          style={{
            fontFamily: FONT.display,
            fontWeight: 700,
            fontSize: compact ? 17 : 18,
            color: T.text,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {title}
        </div>
        <div style={{fontFamily: FONT.mono, fontSize: 13, color: T.faint, marginTop: 6}}>{meta}</div>
        {actions ? (
          <div style={{display: 'flex', gap: 8, marginTop: 12}}>
            <ActionBtn label="Convert" caret />
            <ActionBtn label="Tag" caret />
            <ActionBtn label="⋮" />
          </div>
        ) : null}
      </div>
    </div>
  );
};

export const Chip: React.FC<{
  label: string;
  color: string;
  soft: string;
  size?: number;
}> = ({label, color, soft, size = 18}) => (
  <div
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      fontFamily: FONT.mono,
      fontSize: size,
      textTransform: 'uppercase',
      letterSpacing: '0.1em',
      color,
      background: soft,
      border: `1px solid ${color}44`,
      borderRadius: 999,
      padding: `${size * 0.35}px ${size * 0.85}px`,
    }}
  >
    {label}
  </div>
);

export const ProgressBar: React.FC<{pct: number; height?: number; color?: string}> = ({
  pct,
  height = 12,
  color = T.accent,
}) => (
  <div style={{width: '100%', height, borderRadius: height / 2, background: T.line, overflow: 'hidden'}}>
    <div
      style={{
        width: `${Math.min(100, Math.max(0, pct))}%`,
        height: '100%',
        borderRadius: height / 2,
        background: `linear-gradient(90deg, ${color}, ${T.accentStrong})`,
      }}
    />
  </div>
);

// Typewriter text: reveals `text` between frames [from, to].
export const useTypewriter = (text: string, from: number, to: number): string => {
  const frame = useCurrentFrame();
  const n = Math.round(
    interpolate(frame, [from, to], [0, text.length], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    })
  );
  return text.slice(0, n);
};

export type CursorKey = {f: number; x: number; y: number};

// Animated mouse cursor following keyframes; renders click ripples.
export const Cursor: React.FC<{path: CursorKey[]; clicks?: number[]}> = ({path, clicks = []}) => {
  const frame = useCurrentFrame();
  const fs = path.map((p) => p.f);
  const x = interpolate(frame, fs, path.map((p) => p.x), {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const y = interpolate(frame, fs, path.map((p) => p.y), {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const clicking = clicks.some((c) => frame >= c && frame <= c + 6);
  const visible = frame >= fs[0] - 5;
  if (!visible) return null;
  return (
    <>
      {clicks.map((c) =>
        frame >= c && frame <= c + 20 ? (
          <div
            key={c}
            style={{
              position: 'absolute',
              left: x - 26,
              top: y - 26,
              width: 52,
              height: 52,
              borderRadius: 26,
              border: `3px solid ${T.accent}`,
              opacity: interpolate(frame, [c, c + 20], [0.9, 0]),
              transform: `scale(${interpolate(frame, [c, c + 20], [0.4, 1.5])})`,
              zIndex: 40,
            }}
          />
        ) : null
      )}
      <svg
        width={30}
        height={34}
        viewBox="0 0 13 19"
        style={{
          position: 'absolute',
          left: x,
          top: y,
          zIndex: 41,
          transform: `scale(${clicking ? 0.85 : 1})`,
          filter: 'drop-shadow(0 2px 5px rgba(0,0,0,0.6))',
        }}
      >
        <path
          d="M0 0 L0 16 L4.5 12.5 L7.5 19 L10 18 L7 11.5 L12 11 Z"
          fill="#ffffff"
          stroke="#1c1b18"
          strokeWidth={1}
        />
      </svg>
    </>
  );
};

// Small caption pinned near the bottom of the screen.
export const Caption: React.FC<{text: string; delay?: number}> = ({text, delay = 0}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: frame - delay, fps, config: {damping: 200}});
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 34,
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        opacity: s,
      }}
    >
      <div
        style={{
          fontFamily: FONT.mono,
          fontSize: 24,
          color: T.dim,
          background: T.surface,
          border: `1px solid ${T.line}`,
          borderRadius: 999,
          padding: '12px 30px',
        }}
      >
        {text}
      </div>
    </div>
  );
};
