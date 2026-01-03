import React from 'react';
import { formatCurrency } from '../../utils/helpers';

/**
 * Panier B2B
 */
const B2BCart = ({ cartItems, onRemoveItem, onUpdateQuantity, onCheckout, loading }) => {
	const calculateTotal = () => {
		return cartItems.reduce((total, item) => {
			return total + (item.b2b_price || item.price) * item.quantity;
		}, 0);
	};

	if (!cartItems || cartItems.length === 0) {
		return (
			<div className="bg-white rounded-lg shadow p-6 text-center">
				<p className="text-gray-500">Votre panier est vide</p>
			</div>
		);
	}

	return (
		<div className="bg-white rounded-lg shadow">
			<div className="p-6 border-b border-gray-200">
				<h2 className="text-xl font-bold">Panier B2B</h2>
			</div>

			<div className="p-6 space-y-4">
				{cartItems.map((item) => (
					<div key={item.id} className="flex items-center gap-4 pb-4 border-b border-gray-200">
						{/* Image */}
						<img
							src={item.image || '/placeholder.png'}
							alt={item.name}
							className="w-16 h-16 object-cover rounded"
							onError={(e) => {
								e.target.src = '/placeholder.png';
							}}
						/>

						{/* Details */}
						<div className="flex-1">
							<h3 className="font-semibold">{item.name}</h3>
							<p className="text-sm text-gray-600">
								{formatCurrency(item.b2b_price || item.price)} × {item.quantity}
							</p>
						</div>

						{/* Quantity */}
						<div className="flex items-center gap-2">
							<button
								onClick={() => onUpdateQuantity?.(item.id, item.quantity - 1)}
								disabled={item.quantity <= 1}
								className="w-8 h-8 flex items-center justify-center border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
							>
								-
							</button>
							<span className="w-12 text-center">{item.quantity}</span>
							<button
								onClick={() => onUpdateQuantity?.(item.id, item.quantity + 1)}
								disabled={item.quantity >= item.stock}
								className="w-8 h-8 flex items-center justify-center border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
							>
								+
							</button>
						</div>

						{/* Subtotal */}
						<div className="text-right">
							<p className="font-semibold">
								{formatCurrency((item.b2b_price || item.price) * item.quantity)}
							</p>
						</div>

						{/* Remove */}
						<button
							onClick={() => onRemoveItem?.(item.id)}
							className="text-red-600 hover:text-red-700 p-2"
							title="Retirer du panier"
						>
							<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									strokeWidth={2}
									d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
								/>
							</svg>
						</button>
					</div>
				))}
			</div>

			{/* Total */}
			<div className="p-6 border-t border-gray-200 bg-gray-50">
				<div className="flex justify-between items-center mb-4">
					<span className="text-lg font-semibold">Total</span>
					<span className="text-2xl font-bold text-cta-600">
						{formatCurrency(calculateTotal())}
					</span>
				</div>

				<button
					onClick={onCheckout}
					disabled={loading}
					className="w-full bg-cta-600 text-white py-3 rounded-lg hover:bg-cta-700 transition-colors font-semibold disabled:bg-gray-300 disabled:cursor-not-allowed"
				>
					{loading ? 'Traitement...' : 'Passer la commande'}
				</button>
			</div>
		</div>
	);
};

export default B2BCart;

