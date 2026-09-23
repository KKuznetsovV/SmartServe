import type { ThemePreference } from './theme'

/**
 * Static markup for a blocking inline script placed at the start of `<body>`.
 * It applies the resolved theme before first paint (based on the server-read
 * cookie value passed in), so there is no flash of the wrong theme while React
 * hydrates. Contains no user input — safe for `dangerouslySetInnerHTML`.
 *
 * Deliberately kept out of theme.tsx (which is `'use client'`) so it can be
 * called from Server Components like `layout.tsx` without triggering
 * "Attempted to call ... from the server but ... is on the client".
 */
export function getNoFlashThemeScript(serverTheme: ThemePreference): string {
  return `(function(){try{if(${JSON.stringify(serverTheme)}==='dark')document.documentElement.classList.add('dark');}catch(e){}})();`
}
