import React from 'react';
import {AbsoluteFill, Composition, Series} from 'remotion';
import {Intro} from './scenes/Intro';
import {Download} from './scenes/Download';
import {Organize} from './scenes/Organize';
import {Convert} from './scenes/Convert';
import {Watch} from './scenes/Watch';
import {Outro} from './scenes/Outro';
import {T} from './theme';

const SCENES: [React.FC, number][] = [
  [Intro, 150],
  [Download, 420],
  [Watch, 360],
  [Organize, 400],
  [Convert, 330],
  [Outro, 290],
];

const TOTAL = SCENES.reduce((sum, [, d]) => sum + d, 0);

const Guide: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: T.bg}}>
    <Series>
      {SCENES.map(([Comp, duration], i) => (
        <Series.Sequence key={i} durationInFrames={duration}>
          <Comp />
        </Series.Sequence>
      ))}
    </Series>
  </AbsoluteFill>
);

export const Root: React.FC = () => (
  <Composition
    id="MediaBoxGuide"
    component={Guide}
    durationInFrames={TOTAL}
    fps={30}
    width={1920}
    height={1080}
  />
);
