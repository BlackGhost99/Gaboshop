import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDownIcon, ChevronRightIcon } from '@heroicons/react/24/outline';

// Rapport financier détaillé : ventes livrées par catégorie, avec les commandes qui les composent.
// Outil du forfait (commerces et grossistes) : sans lui, on dit honnêtement pourquoi et quel forfait l'offre.

const formatCurrency = (amount) =>
  new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(Number(amount) || 0) + ' FCFA';

const formatDate = (iso) => {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
};

const CategoryDetailedReport = ({ report = [], detailedReport }) => {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState({});
  const available = detailedReport?.available === true;
  const toggle = (key) => setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="w-full flex items-center justify-between gap-3 px-6 py-4 text-left"
        aria-expanded={open}
      >
        <span>
          <span className="block text-lg font-semibold text-gray-900">Rapport détaillé par catégorie</span>
          <span className="block text-sm text-gray-500">Ventes livrées de chaque catégorie, commande par commande</span>
        </span>
        {open ? <ChevronDownIcon className="w-5 h-5 text-gray-500 shrink-0" /> : <ChevronRightIcon className="w-5 h-5 text-gray-500 shrink-0" />}
      </button>

      {open && (
        <div className="px-6 pb-6">
          {!available ? (
            <div className="bg-amber-50 border border-amber-200 text-amber-900 rounded px-4 py-3 text-sm break-words">
              <p>{detailedReport?.message || "Le rapport financier détaillé n'est pas inclus dans votre forfait."}</p>
              <Link to="/store/subscription" className="inline-block mt-2 font-semibold underline">Voir « Mon forfait »</Link>
            </div>
          ) : report.length === 0 ? (
            <p className="text-sm text-gray-600">Aucune vente livrée sur la période choisie.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-600 border-b border-gray-200">
                    <th className="py-2 pr-4 font-medium">Catégorie</th>
                    <th className="py-2 pr-4 font-medium text-right">Commandes</th>
                    <th className="py-2 pr-4 font-medium text-right">Articles</th>
                    <th className="py-2 font-medium text-right">Ventes</th>
                  </tr>
                </thead>
                <tbody>
                  {report.map((category) => {
                    const key = category.category_id ?? 'none';
                    const isOpen = !!expanded[key];
                    return (
                      <FragmentRows key={key} category={category} isOpen={isOpen} onToggle={() => toggle(key)} />
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-gray-300 font-semibold text-gray-900">
                    <td className="py-2 pr-4">Total</td>
                    <td className="py-2 pr-4 text-right">{report.reduce((sum, c) => sum + c.orders_count, 0)}</td>
                    <td className="py-2 pr-4 text-right">{report.reduce((sum, c) => sum + Number(c.items_sold || 0), 0)}</td>
                    <td className="py-2 text-right">{formatCurrency(report.reduce((sum, c) => sum + Number(c.total_sales || 0), 0))}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const FragmentRows = ({ category, isOpen, onToggle }) => (
  <>
    <tr className="border-b border-gray-100 hover:bg-gray-50">
      <td className="py-2 pr-4">
        <button type="button" onClick={onToggle} className="flex items-center gap-2 text-left font-medium text-gray-900" aria-expanded={isOpen}>
          {isOpen ? <ChevronDownIcon className="w-4 h-4 shrink-0" /> : <ChevronRightIcon className="w-4 h-4 shrink-0" />}
          <span className="break-words">{category.category_name}</span>
        </button>
      </td>
      <td className="py-2 pr-4 text-right text-gray-700">{category.orders_count}</td>
      <td className="py-2 pr-4 text-right text-gray-700">{category.items_sold}</td>
      <td className="py-2 text-right font-medium text-gray-900">{formatCurrency(category.total_sales)}</td>
    </tr>
    {isOpen && category.orders.map((order) => (
      <tr key={`${category.category_id}-${order.order_id}`} className="bg-gray-50 text-gray-700">
        <td className="py-1.5 pl-8 pr-4 break-words">
          #{order.order_number} · {order.buyer_name}{order.is_b2b ? ' (commerce)' : ''}
          <span className="block text-xs text-gray-500">{formatDate(order.created_at)}</span>
        </td>
        <td className="py-1.5 pr-4 text-right">1</td>
        <td className="py-1.5 pr-4 text-right">{order.items_sold}</td>
        <td className="py-1.5 text-right">{formatCurrency(order.sales)}</td>
      </tr>
    ))}
  </>
);

export default CategoryDetailedReport;
