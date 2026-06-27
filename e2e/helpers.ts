import { test } from '@playwright/test';

/**
 * Base URL of the running Vibe-Trading web app.
 * Override with E2E_APP_URL if the app runs elsewhere.
 */
export const APP_URL = process.env.E2E_APP_URL ?? 'http://127.0.0.1:8899';

let reachable: boolean | undefined;

/** True when the Vibe-Trading server responds. Cached for the run. */
export async function appReachable(): Promise<boolean> {
  if (reachable === undefined) {
    try {
      const res = await fetch(APP_URL, { method: 'GET' });
      reachable = res.status > 0 && res.status < 500;
    } catch {
      reachable = false;
    }
  }
  return reachable;
}

/** Skip the enclosing suite when the local app is not running (e.g. in CI). */
export async function skipIfAppDown(): Promise<void> {
  test.skip(!(await appReachable()), 'Vibe-Trading server not reachable');
}
