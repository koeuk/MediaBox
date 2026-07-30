import {loadFont as loadArchivo} from '@remotion/google-fonts/Archivo';
import {loadFont as loadPlexMono} from '@remotion/google-fonts/IBMPlexMono';

const archivo = loadArchivo();
const plexMono = loadPlexMono();

// MediaBox dark-theme design tokens (frontend/app/assets/css/main.css)
export const T = {
  bg: '#0d0e10',
  bgRaised: '#141619',
  surface: '#17191d',
  surfaceHover: '#1d2025',
  line: '#26292f',
  lineStrong: '#34383f',
  text: '#eae7e0',
  dim: '#9297a1',
  faint: '#5c616b',
  accent: '#f2a33c',
  accentStrong: '#ffb454',
  accentInk: '#191002',
  accentSoft: 'rgba(242, 163, 60, 0.12)',
  ok: '#55c47c',
  okSoft: 'rgba(85, 196, 124, 0.12)',
  err: '#e5484d',
  errSoft: 'rgba(229, 72, 77, 0.12)',
};

export const FONT = {
  display: archivo.fontFamily,
  mono: plexMono.fontFamily,
};
