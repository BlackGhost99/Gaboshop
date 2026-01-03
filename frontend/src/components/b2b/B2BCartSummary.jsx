import React from 'react';
import { formatCurrency } from '../../utils/helpers';

/**
 * Composant de résumé du panier B2B affiché dans l'en-tête du catalogue
 */
const B2BCartSummary = ({ cartItems, onViewCart, totalAmount }) => {
	const itemCount = cartItems?.length || 0;
	const total = totalAmount || cartItems?.reduce((sum, item) => {
		return sum + (item.b2b_price || item.price) * item.quantity;
	}, 0) || 0;

	if (itemCount === 0) {
		return (
			<div className="bg-gray-100 rounded-lg p-4 border-2 border-dashed border-gray-300">
				<div className="flex items-center gap-3">
					<div className="bg-gray-400 rounded-full p-2">
						<svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4m0 0L7 13m0 0l-2.5 5M7 13l-2.5 5m0 0l-1.5 3h15M17 18v2a2 2 0 01-2 2H9a2 2 0 01-2-2v-2m8-10V5a2 2 0 00-2-2H9a2 2 0 00-2 2v3.01" />
						</svg>
					</div>
					<div>
						<p className="text-sm text-gray-600 font-medium">Panier vide</p>
						<p className="text-xs text-gray-500">Ajoutez des produits</p>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="bg-green-50 rounded-lg p-4 border-2 border-green-300 shadow-md">
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-3">
					<div className="bg-green-600 rounded-full p-2">
						<svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4m0 0L7 13m0 0l-2.5 5M7 13l-2.5 5m0 0l-1.5 3h15M17 18v2a2 2 0 01-2 2H9a2 2 0 01-2-2v-2m8-10V5a2 2 0 00-2-2H9a2 2 0 00-2 2v3.01" />
						</svg>
					</div>
					<div>
						<p className="font-bold text-black">{itemCount} article{itemCount > 1 ? 's' : ''}</p>
						<p className="text-lg font-bold text-green-700">{formatCurrency(total)}</p>
					</div>
				</div>
				<button
					onClick={onViewCart}
					style={{ backgroundColor: '#16A34A' }}
					className="text-white px-6 py-3 rounded-xl hover:bg-green-700 font-bold flex items-center gap-3 shadow-lg border-2 border-green-700"
				>
					<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
					</svg>
					Voir panier
				</button>
			</div>
		</div>
	);
};

export default B2BCartSummary;
