import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Memory Cues Heatmap',
  description: 'View Memory Cues Heatmap in the Discovery Engine',
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
