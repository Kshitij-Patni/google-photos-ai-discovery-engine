import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Behavior Patterns',
  description: 'View Behavior Patterns in the Discovery Engine',
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
