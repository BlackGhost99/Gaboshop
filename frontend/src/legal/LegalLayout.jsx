import React, { useEffect } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { COMPANY, LEGAL_PAGES } from './legalInfo';

/** Section titrée d'une page légale. */
export function Section({ id, title, children }) {
  return (
    <section id={id} className="mt-8 scroll-mt-4">
      <h2 className="text-lg sm:text-xl font-bold text-gray-900 mb-3">{title}</h2>
      <div className="space-y-3 text-[15px] leading-relaxed text-gray-700">{children}</div>
    </section>
  );
}

/** Liste à puces simple. */
export function List({ items }) {
  return (
    <ul className="list-disc pl-5 space-y-1.5">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}

/**
 * Mise en page commune des pages légales publiques (mobile d'abord).
 */
export default function LegalLayout({ title, intro, children }) {
  useEffect(() => {
    document.title = `${title} | ${COMPANY.brand}`;
    window.scrollTo(0, 0);
  }, [title]);

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2 min-w-0">
            <span className="w-8 h-8 shrink-0 bg-primary-600 rounded-lg flex items-center justify-center text-white font-bold">
              G
            </span>
            <span className="font-bold text-gray-900 truncate">GABOSHOP</span>
          </Link>
          <Link to="/" className="text-sm text-indigo-600 hover:text-indigo-500 shrink-0">
            ← Accueil
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 sm:py-10">
        <article className="bg-white shadow sm:rounded-lg px-4 py-6 sm:px-8 sm:py-8 break-words">
          <div
            role="note"
            className="mb-5 rounded-md border border-cta-300 bg-cta-50 px-3 py-2 text-sm font-medium text-cta-800"
          >
            Version provisoire, en cours de validation juridique.
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900">{title}</h1>
          <p className="mt-2 text-sm text-gray-500">Dernière mise à jour : {COMPANY.updatedAt}</p>
          {intro && <p className="mt-4 text-[15px] leading-relaxed text-gray-700">{intro}</p>}

          {children}
        </article>

        <nav aria-label="Pages légales" className="mt-6">
          <ul className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
            {LEGAL_PAGES.map((page) => (
              <li key={page.path}>
                <NavLink
                  to={page.path}
                  className={({ isActive }) =>
                    isActive ? 'font-semibold text-gray-900' : 'text-indigo-600 hover:text-indigo-500 underline'
                  }
                >
                  {page.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-gray-500">
            © {new Date().getFullYear()} {COMPANY.brand} · {COMPANY.city} · Contact : {COMPANY.email}
          </p>
        </nav>
      </main>
    </div>
  );
}
