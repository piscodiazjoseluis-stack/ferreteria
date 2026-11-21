import { copyFile, mkdir } from 'node:fs/promises'
// Physical SPA entry for Vercel Services' static router, also on clean deployments.
await mkdir(new URL('../dist/catalogo/', import.meta.url), { recursive: true })
await copyFile(new URL('../dist/index.html', import.meta.url), new URL('../dist/catalogo/index.html', import.meta.url))
await copyFile(new URL('../dist/index.html', import.meta.url), new URL('../dist/catalogo.html', import.meta.url))
