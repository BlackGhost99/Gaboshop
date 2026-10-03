// Build the frontend for Android and copy it into the native project.
//   node scripts/android-sync.mjs dev   -> API from .env.android-dev (local Django)
//   node scripts/android-sync.mjs prod  -> API from .env.android (must be HTTPS)
import { spawnSync } from 'node:child_process';
import { loadEnv } from 'vite';

const target = process.argv[2];
if (!['dev', 'prod'].includes(target)) {
  console.error('Usage: node scripts/android-sync.mjs <dev|prod>');
  process.exit(1);
}

const mode = target === 'dev' ? 'android-dev' : 'android';
const apiUrl = loadEnv(mode, process.cwd(), 'VITE_').VITE_API_URL || '';

if (target === 'prod' && !apiUrl.startsWith('https://')) {
  console.error(`VITE_API_URL dans .env.android doit être une URL https:// (actuel : "${apiUrl}").`);
  process.exit(1);
}
console.log(`[android:${target}] API = ${apiUrl}`);

const run = (cmd, env = {}) => {
  const res = spawnSync(cmd, { stdio: 'inherit', shell: true, env: { ...process.env, ...env } });
  if (res.status !== 0) process.exit(res.status ?? 1);
};

run(`npx vite build --mode ${mode}`);
run('npx cap sync android', { CAP_DEV: target === 'dev' ? '1' : '0' });
