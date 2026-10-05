import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Evidence Browser',
  description: 'View Evidence Browser in the Discovery Engine',
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
