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
				<p className="text-gray-500">Aucun produit disponible</p>
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
							{product.b2b_price && product.price && product.b2b_price < product.price && (
								<div className="absolute top-3 right-3 bg-green-600 text-white px-3 py-1 rounded-full text-xs font-bold">
									Prix B2B
								</div>
							)}
						</div>

						{/* Content */}
						<div className="p-4">
							<h3 className="font-bold text-lg mb-2">{product.name}</h3>
							<p className="text-gray-600 text-sm mb-3 line-clamp-2">{product.description}</p>

							{/* Prix */}
							<div className="mb-3">
								{b2bPrice ? (
									<div>
										<p className="text-2xl font-bold text-cta-600">
											{formatCurrency(b2bPrice)}
										</p>
										{product.price && b2bPrice < product.price && (
											<p className="text-sm text-gray-500 line-through">
												{formatCurrency(product.price)}
											</p>
										)}
										{product.pricing_tiers && product.pricing_tiers.length > 1 && (
											<div className="mt-2 space-y-1">
												<p className="text-xs font-semibold text-gray-500">Paliers de prix :</p>
												{product.pricing_tiers.map((tier, idx) => (
													<p key={idx} className="text-xs text-blue-600">
														Dès {tier.min_qty} unités : {formatCurrency(tier.price)}
													</p>
												))}
											</div>
										)}
									</div>
								) : (
									<p className="text-gray-500">Prix B2B non disponible</p>
								)}
							</div>

							{/* Stock */}
							<p className="text-sm text-gray-600 mb-3">
								Stock: {product.stock} unité(s)
							</p>

							{/* Quantité */}
							<div className="mb-3">
								<label className="block text-sm font-semibold mb-1">Quantité</label>
								<div className="flex items-center gap-2">
									<input
										type="number"
										min={minQuantity}
										max={maxQuantity || product.stock}
										value={currentQuantity}
										onChange={(e) => handleQuantityChange(product.id, e.target.value)}
										className="flex-1 border border-gray-300 rounded px-3 py-2"
									/>
									{maxQuantity && (
										<span className="text-xs text-gray-500">Max: {maxQuantity}</span>
									)}
								</div>
								<p className="text-xs text-gray-500 mt-1">
									Quantité minimum: {minQuantity}
								</p>
							</div>

							{/* Add to cart */}
							<button
								onClick={() => handleAddToCart(product)}
								disabled={!b2bPrice || (product.in_stock === false) || product.stock < minQuantity}
								className="w-full bg-cta-600 text-white py-2 rounded-lg hover:bg-cta-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
							>
								{product.in_stock === false ? 'Rupture de stock' : 'Ajouter au panier'}
							</button>
						</div>
					</div>
				);
			})}
		</div>
	);
};

export default B2BProductList;

