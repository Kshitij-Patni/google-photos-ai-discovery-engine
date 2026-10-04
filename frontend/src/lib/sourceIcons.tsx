/**
 * Actual brand SVG icons for data sources.
 * Used in source badges (evidence page) and dashboard sources strip.
 */

interface IconProps {
  size?: number;
}

/** Official YouTube logo — red pill + white triangle */
export function YouTubeIcon({ size = 16 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-label="YouTube">
      <path
        fill="#FF0000"
        d="M23.495 6.205a3.007 3.007 0 0 0-2.088-2.088C19.538 3.6 12 3.6 12 3.6s-7.538 0-9.407.517A3.007 3.007 0 0 0 .505 6.205 31.247 31.247 0 0 0 0 12a31.247 31.247 0 0 0 .505 5.795 3.007 3.007 0 0 0 2.088 2.088C4.462 20.4 12 20.4 12 20.4s7.538 0 9.407-.517a3.007 3.007 0 0 0 2.088-2.088A31.247 31.247 0 0 0 24 12a31.247 31.247 0 0 0-.505-5.795z"
      />
      <path fill="#FFFFFF" d="M9.6 15.6V8.4l6.4 3.6-6.4 3.6z" />
    </svg>
  );
}

/** Google Play Store logo — 4-color triangle arrow */
export function PlayStoreIcon({ size = 16 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 512 512" aria-label="Google Play Store">
      <path fill="#00C1FF" d="M30.06 8.6C18.72 15.06 11 27.28 11 41.4v429.2c0 14.12 7.72 26.34 19.06 32.8L272 256 30.06 8.6z" />
      <path fill="#FFBC00" d="M360.1 174.4 75.22 11.16 72.6 9.74 272 256l88.1-81.6z" />
      <path fill="#FF3D00" d="M360.1 337.6 272 256 72.6 502.26l2.62-1.42L360.1 337.6z" />
      <path fill="#00F076" d="M482.48 219.56l-77.8-44.56L272 256l132.68 80.98 77.8-44.56C502.54 281 502.54 231 482.48 219.56z" />
    </svg>
  );
}

/** Apple App Store logo — standard Apple logo */
export function AppStoreIcon({ size = 16 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 384 512" aria-label="Apple App Store">
      <path
        fill="currentColor"
        d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.1-44.6-35.9-2.8-74.3 22.7-93.1 22.7-18.9 0-46.5-20.9-76.3-20.9-39.7 0-81.5 24.3-103.5 63.8-44.6 79.5-27.5 197.6 16.4 260.6 21.6 31 48 64 80.6 62.7 31.7-1.3 43.6-20.6 82.2-20.6 38.3 0 49.3 20.6 82.2 20.2 34.2-.4 57.5-30.8 78.8-62 25.1-36.7 35.5-72.3 36-74.1-1.3-.7-68.5-25.5-69.2-123zm-113.8-193.5c20.3-25.1 34.1-59.8 30.3-95.2-29.6 1.4-67.4 20.3-88.6 45.9-18.9 22.6-34.5 58.3-30.1 92.5 33.3 2.6 69.1-19.1 88.4-43.2z"
      />
    </svg>
  );
}

/** Reddit logo (future source placeholder if needed) */
export function RedditIcon({ size = 16 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-label="Reddit">
      <circle cx="12" cy="12" r="12" fill="#FF4500" />
      <path
        fill="#FFFFFF"
        d="M20 12a2 2 0 0 0-2-2 2 2 0 0 0-1.25.44A9.6 9.6 0 0 0 12.5 9.5l.8-3.76 2.61.55a1.5 1.5 0 1 0 .18-.9L13.5 4.8l-.96 4.5a9.7 9.7 0 0 0-4.22.94A2 2 0 0 0 4 12a2 2 0 0 0 1 1.74A3.6 3.6 0 0 0 5 14c0 2.21 3.13 4 7 4s7-1.79 7-4a3.6 3.6 0 0 0-.04-.26A2 2 0 0 0 20 12zm-13 2c0-.55.45-1 1-1s1 .45 1 1-.45 1-1 1-1-.45-1-1zm5.5 2.5c-.83 0-1.5-.2-1.5-.44s.67-.44 1.5-.44 1.5.2 1.5.44-.67.44-1.5.44zm2.5-1.5c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1z"
      />
    </svg>
  );
}

/** Google G Logo (used for Support Forums) */
export function GoogleSupportIcon({ size = 16 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-label="Google Support">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
  );
}

/** Map source key → display config */
export const SOURCE_CONFIG: Record<string, {
  label: string;
  Icon: React.FC<IconProps>;
  badgeClass: string;
  color: string;
}> = {
  play_store: {
    label: 'Play Store',
    Icon: PlayStoreIcon,
    badgeClass: 'source-badge--play-store',
    color: '#01875f',
  },
  app_store: {
    label: 'App Store',
    Icon: AppStoreIcon,
    badgeClass: 'source-badge--app-store',
    color: '#2072F3',
  },
  youtube: {
    label: 'YouTube',
    Icon: YouTubeIcon,
    badgeClass: 'source-badge--youtube',
    color: '#FF0000',
  },
  support_forums: {
    label: 'Support Forums',
    Icon: GoogleSupportIcon,
    badgeClass: 'source-badge--support',
    color: '#4285F4',
  },
};
