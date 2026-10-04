#!/bin/sh
# Runs inside the `android` container. Output: /out/gaboshop-<mode>.apk
set -e
cd /app

# Reinstall dependencies only when package-lock.json changed
LOCK_HASH=$(sha256sum package-lock.json | cut -d' ' -f1)
if [ "$(cat node_modules/.lock-hash 2>/dev/null)" != "$LOCK_HASH" ]; then
  npm ci
  echo "$LOCK_HASH" > node_modules/.lock-hash
fi

node scripts/android-sync.mjs "${APK_MODE:-dev}"

cd android
sh ./gradlew assembleDebug --no-daemon -q
cp app/build/outputs/apk/debug/app-debug.apk "/out/gaboshop-${APK_MODE:-dev}.apk"
echo "APK prêt : builds/android/gaboshop-${APK_MODE:-dev}.apk (API = $VITE_API_URL)"
