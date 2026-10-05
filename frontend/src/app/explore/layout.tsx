import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Q&A Explorer',
  description: 'View Q&A Explorer in the Discovery Engine',
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
