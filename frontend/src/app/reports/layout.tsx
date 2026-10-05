import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Generated Reports',
  description: 'View Generated Reports in the Discovery Engine',
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
