'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_ITEMS = [
  { href: '/', label: 'Dashboard', icon: '📊' },
  { href: '/explore', label: 'Explore', icon: '🔍' },
  { href: '/archetypes', label: 'Archetypes', icon: '🧩' },
  { href: '/memory-cues', label: 'Memory Cues', icon: '🧠' },
  { href: '/behaviors', label: 'Behaviors', icon: '🔄' },
  { href: '/evidence', label: 'Evidence', icon: '📝' },
  { href: '/reports', label: 'Reports & Charts', icon: '📈' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <nav className="sidebar__nav">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === '/'
              ? pathname === '/'
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar__link ${isActive ? 'sidebar__link--active' : ''}`}
            >
              <span className="sidebar__icon">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
