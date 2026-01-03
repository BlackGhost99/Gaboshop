import React, { useState } from 'react';
import { formatCurrency } from '../../utils/helpers';

/**
 * Liste des produits B2B
 */
const B2BProductList = ({ products, onAddToCart, loading }) => {
	const [quantities, setQuantities] = useState({});

	const handleQuantityChange = (productId, value) => {
		setQuantities((prev) => ({
			...prev,
			[productId]: Math.max(1, parseInt(value) || 1),
		}));
	};

	const handleAddToCart = (product) => {
		const quantity = quantities[product.id] || product.min_order_quantity || product.b2b_pricings?.[0]?.min_quantity || 1;
		onAddToCart?.(product, quantity);
	};

	if (loading) {
		return (
			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{[...Array(6)].map((_, i) => (
					<div key={i} className="bg-white rounded-lg shadow p-4 animate-pulse">
						<div className="h-32 bg-gray-200 rounded mb-4"></div>
						<div className="h-4 bg-gray-200 rounded mb-2"></div>
						<div className="h-4 bg-gray-200 rounded w-2/3"></div>
					</div>
				))}
			</div>
		);
	}

	if (!products || products.length === 0) {
		return (
			<div className="text-center py-12">
				<p className="text-black font-medium">Aucun produit disponible</p>
			</div>
		);
	}

	return (
		<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{products.map((product) => {
				const b2bPrice = product.wholesale_price || product.b2b_price || product.b2b_pricings?.[0]?.b2b_price;
				const minQuantity = product.min_order_quantity || product.b2b_pricings?.[0]?.min_quantity || 1;
				const maxQuantity = product.b2b_pricings?.[0]?.max_quantity;
				const currentQuantity = quantities[product.id] || minQuantity;

				return (
					<div
						key={product.id}
						className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow overflow-hidden"
					>
						{/* Image */}
						<div className="relative h-48 bg-gray-200">
							<img
								src={product.image || '/placeholder.png'}
								alt={product.name}
								className="w-full h-full object-cover"
								onError={(e) => {
									e.target.src = '/placeholder.png';
								}}
							/>
						</div>

						{/* Content */}
						<div className="p-4">
							<h3 className="font-bold text-lg mb-2 text-black">{product.name}</h3>
							<p className="text-black text-sm mb-3 line-clamp-2 font-medium">{product.description}</p>

							{/* Prix */}
							<div className="mb-4 p-3 bg-gradient-to-r from-indigo-50 to-blue-50 rounded-lg border border-indigo-200">
								{b2bPrice ? (
									<div>
										<div className="flex items-center gap-2 mb-2">
											<span className="bg-indigo-600 text-white px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide">
												Prix B2B
											</span>
											{product.price && b2bPrice < product.price && (
												<span className="bg-green-600 text-white px-2 py-1 rounded-full text-xs font-bold">
													Économie: {Math.round(((product.price - b2bPrice) / product.price) * 100)}%
												</span>
											)}
										</div>
										<p className="text-3xl font-bold text-indigo-700 mb-1">
											{formatCurrency(b2bPrice)}
										</p>
										{product.price && b2bPrice < product.price && (
											<p className="text-sm text-gray-500 line-through font-medium">
												Prix retail: {formatCurrency(product.price)}
											</p>
										)}
										{product.pricing_tiers && product.pricing_tiers.length > 1 && (
											<div className="mt-3 space-y-1">
												<p className="text-xs font-bold text-indigo-800 bg-indigo-100 px-2 py-1 rounded">Paliers de prix :</p>
												{product.pricing_tiers.map((tier, idx) => (
													<p key={idx} className="text-xs text-indigo-700 font-semibold bg-indigo-50 px-2 py-1 rounded">
														Dès {tier.min_qty} unités : {formatCurrency(tier.price)}
													</p>
												))}
											</div>
										)}
									</div>
								) : (
									<p className="text-gray-500 font-medium">Prix B2B non disponible</p>
								)}
							</div>

							{/* Stock */}
							<p className="text-sm text-black font-bold mb-3">
								Stock: {product.stock} unité(s)
							</p>

							{/* Quantité */}
							<div className="mb-3">
								<label className="block text-sm font-bold text-black mb-1">Quantité</label>
								<div className="flex items-center gap-2">
									<input
										type="number"
										min={minQuantity}
										max={maxQuantity || product.stock}
										value={currentQuantity}
										onChange={(e) => handleQuantityChange(product.id, e.target.value)}
										className="flex-1 border-2 border-gray-400 rounded px-3 py-2 text-black font-semibold"
									/>
									{maxQuantity && (
										<span className="text-xs text-black font-bold">Max: {maxQuantity}</span>
									)}
								</div>
								<p className="text-xs text-black font-bold mt-1">
									Quantité minimum: {minQuantity}
								</p>
							</div>

							{/* Add to cart */}
							<button
								onClick={() => handleAddToCart(product)}
								disabled={!b2bPrice || (product.in_stock === false) || product.stock < minQuantity}
								style={{ backgroundColor: '#16A34A' }}
								className="w-full text-white py-4 px-6 rounded-xl hover:bg-green-700 disabled:!bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-3 font-bold text-xl shadow-lg border-2 border-green-700"
							>
								{product.in_stock === false ? (
									<>
										<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
										</svg>
										Rupture de stock
									</>
								) : (
									<>
										<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4m0 0L7 13m0 0l-2.5 5M7 13l-2.5 5m0 0l-1.5 3h15M17 18v2a2 2 0 01-2 2H9a2 2 0 01-2-2v-2m8-10V5a2 2 0 00-2-2H9a2 2 0 00-2 2v3.01" />
										</svg>
										Ajouter au panier
									</>
								)}
							</button>
						</div>
					</div>
				);
			})}
		</div>
	);
};

export default B2BProductList;

