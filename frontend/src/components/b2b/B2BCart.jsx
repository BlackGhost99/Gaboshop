import React from 'react';
import { formatCurrency } from '../../utils/helpers';

/**
 * Panier B2B
 */
const B2BCart = ({ cartItems, onRemoveItem, onUpdateQuantity, onCheckout, loading, wholesaler }) => {
	const calculateSubtotal = () => {
		return cartItems.reduce((total, item) => {
			return total + (item.b2b_price || item.price) * item.quantity;
		}, 0);
	};

	const calculateTotal = () => {
		const subtotal = calculateSubtotal();
		// Pour B2B, on peut ajouter des frais de livraison plus tard
		return subtotal;
	};

	const getMinOrderAmount = () => {
		return wholesaler?.minimum_order_amount || wholesaler?.b2b_profile?.minimum_order_amount || 0;
	};

	const isMinOrderMet = () => {
		return calculateSubtotal() >= getMinOrderAmount();
	};

	if (!cartItems || cartItems.length === 0) {
		return (
			<div className="bg-white rounded-lg shadow-lg border-2 border-dashed border-gray-300 p-6 text-center">
				<div className="mb-4">
					<svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 3h2l.4 2M7 13h10l4-8H5.4m0 0L7 13m0 0l-2.5 5M7 13l-2.5 5m0 0l-1.5 3h15M17 18v2a2 2 0 01-2 2H9a2 2 0 01-2-2v-2m8-10V5a2 2 0 00-2-2H9a2 2 0 00-2 2v3.01" />
					</svg>
				</div>
				<p className="text-black font-semibold text-lg mb-2">Votre panier est vide</p>
				<p className="text-gray-600 text-sm">Ajoutez des produits pour commencer votre commande B2B</p>
			</div>
		);
	}

	return (
		<div className="bg-white rounded-lg shadow-lg border-2 border-green-200">
			<div className="p-6 border-b-2 border-green-300 bg-gradient-to-r from-green-50 to-white">
				<div className="flex items-center gap-3">
					<div className="bg-green-600 rounded-full p-2">
						<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4m0 0L7 13m0 0l-2.5 5M7 13l-2.5 5m0 0l-1.5 3h15M17 18v2a2 2 0 01-2 2H9a2 2 0 01-2-2v-2m8-10V5a2 2 0 00-2-2H9a2 2 0 00-2 2v3.01" />
						</svg>
					</div>
					<div>
						<h2 className="text-xl font-bold text-black">Panier B2B</h2>
						<p className="text-sm text-gray-600">{cartItems.length} article{cartItems.length > 1 ? 's' : ''}</p>
					</div>
				</div>
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
							<h3 className="font-semibold text-black">{item.name}</h3>
							<p className="text-sm text-black font-semibold">
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
							<span className="w-12 text-center text-black font-bold">{item.quantity}</span>
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
							<p className="font-bold text-black text-lg">
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

			{/* Récapitulatif */}
			<div className="p-6 border-t border-gray-200 bg-gray-50">
				{/* Sous-total */}
				<div className="flex justify-between items-center mb-2">
					<span className="text-sm text-black font-bold">Sous-total</span>
					<span className="text-sm font-bold text-black">
						{formatCurrency(calculateSubtotal())}
					</span>
				</div>

				{/* Minimum de commande */}
				{getMinOrderAmount() > 0 && (
					<div className="mb-3">
						<div className="flex justify-between items-center mb-1">
							<span className="text-xs text-black font-bold">Minimum de commande</span>
							<span className={`text-xs font-bold ${isMinOrderMet() ? 'text-green-800' : 'text-red-800'}`}>
								{formatCurrency(getMinOrderAmount())}
							</span>
						</div>
						{!isMinOrderMet() && (
							<p className="text-xs text-red-800 font-bold mt-1">
								Il manque {formatCurrency(getMinOrderAmount() - calculateSubtotal())} pour valider la commande
							</p>
						)}
					</div>
				)}

				{/* Total */}
				<div className="flex justify-between items-center mb-4 pt-3 border-t-2 border-gray-400">
					<span className="text-lg font-bold text-black">Total</span>
					<span className="text-2xl font-bold text-indigo-700">
						{formatCurrency(calculateTotal())}
					</span>
				</div>

				<button
					onClick={onCheckout}
					disabled={loading || !isMinOrderMet()}
					style={{ backgroundColor: '#16A34A' }}
					className="w-full text-white py-5 px-8 rounded-xl hover:bg-green-700 disabled:!bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-3 font-bold text-xl shadow-xl border-2 border-green-700"
				>
					{loading ? (
						<>
							<svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
								<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
								<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
							Traitement...
						</>
					) : !isMinOrderMet() ? (
						<>
							<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
							</svg>
							Montant minimum non atteint
						</>
					) : (
						<>
							<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Passer la commande
						</>
					)}
				</button>
			</div>
		</div>
	);
};

export default B2BCart;

