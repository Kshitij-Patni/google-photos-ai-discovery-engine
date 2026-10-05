import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Problem Archetypes',
  description: 'View Problem Archetypes in the Discovery Engine',
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
