import type { Metadata } from 'next';

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const resolvedParams = await params;
  const id = resolvedParams.id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  return {
    title: `${id} Archetype`,
    description: `Details for the ${id} archetype`,
  };
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
