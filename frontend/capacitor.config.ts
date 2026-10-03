import type { CapacitorConfig } from '@capacitor/cli';

// CAP_DEV=1 (set by `npm run android:dev`) lets the app reach a local Django
// over plain HTTP, e.g. http://10.0.2.2:8000 from the emulator.
// Release builds keep the secure defaults: HTTPS only.
const dev = process.env.CAP_DEV === '1';

const config: CapacitorConfig = {
  appId: 'com.gaboshop.app',
  appName: 'Gaboshop',
  webDir: 'dist',
  android: {
    allowMixedContent: dev,
  },
  server: dev ? { cleartext: true } : undefined,
};

export default config;
