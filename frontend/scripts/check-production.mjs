// Run after deployment: npm run check:production -- https://droplinks.site
const target = process.argv[2] || 'https://droplinks.site'

if (target === '--help') {
  console.log('Usage: npm run check:production -- https://your-domain.example')
  process.exit(0)
}

try {
  const site = new URL(target)
  if (!['http:', 'https:'].includes(site.protocol) || site.username || site.password) {
    throw new Error('Provide an HTTP(S) site URL without credentials.')
  }

  async function get(path) {
    const started = performance.now()
    const response = await fetch(new URL(path, site), { signal: AbortSignal.timeout(15000) })
    console.log(`${path}: HTTP ${response.status}, ${Math.round(performance.now() - started)} ms to headers`)
    if (!response.ok) throw new Error(`${path} returned HTTP ${response.status}`)
    return response
  }

  const page = await get('/login')
  const html = await page.text()
  const devAssets = /(?:\/@vite\/client|\/_nuxt\/@fs\/|\/_nuxt\/@id\/virtual:|__nuxt_devtools__)/
  if (devAssets.test(html)) {
    throw new Error('The public login page serves Nuxt development assets. Build the frontend and point the proxy at npm start, not npm run dev.')
  }
  if (!html.includes('__NUXT') && !html.includes('id="__nuxt"')) {
    throw new Error('The response is not the expected Nuxt app. Check the domain and reverse proxy.')
  }
  if (/apiBase\s*["']?\s*:\s*["']https?:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?\//.test(html)) {
    throw new Error('The browser API URL points to localhost. Set NUXT_PUBLIC_API_BASE=/api on the production frontend.')
  }
  const health = await (await get('/api/health')).json()
  if (health.status !== 'ok') throw new Error('The API did not report a healthy status.')
  console.log('PASS: login serves a production build and the same-origin API is healthy.')
} catch (error) {
  console.error(`FAIL: ${error.message}`)
  if (error.cause?.code) console.error(`Connection error: ${error.cause.code}`)
  process.exitCode = 1
}
