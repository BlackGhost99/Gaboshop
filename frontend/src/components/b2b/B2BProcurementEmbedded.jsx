import React, { useState, useEffect } from 'react';
import WholesalerList from './WholesalerList';
import WholesalerDetail from './WholesalerDetail';
import B2BProductList from './B2BProductList';
import B2BCart from './B2BCart';
import B2BOrderForm from './B2BOrderForm';
import LoadingSpinner from '../LoadingSpinner';
import {
	getWholesalers,
	getWholesalerCatalog,
	createB2BOrder,
} from '../../services/b2bService';

/**
 * Composant d'approvisionnement B2B intégré dans le dashboard
 * (sans StoreLayout car déjà géré par le parent)
 */
const B2BProcurementEmbedded = () => {
	const [view, setView] = useState('list'); // 'list', 'detail', 'products', 'cart', 'checkout'
	const [wholesalers, setWholesalers] = useState([]);
	const [selectedWholesaler, setSelectedWholesaler] = useState(null);
	const [products, setProducts] = useState([]);
	const [categories, setCategories] = useState([]);
	const [selectedCategory, setSelectedCategory] = useState(null);
	const [cart, setCart] = useState([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);
	const [pagination, setPagination] = useState({
		page: 1,
		total_products: 0,
		total_pages: 1,
	});

	// Charger les grossistes au montage
	useEffect(() => {
		const fetchWholesalers = async () => {
			try {
				setLoading(true);
				setError(null);
				const response = await getWholesalers();
				if (response.success) {
					setWholesalers(response.data || []);
				} else {
					setError(response.error?.message || 'Erreur lors du chargement des grossistes');
				}
			} catch (err) {
				setError(err.response?.data?.error?.message || 'Erreur lors du chargement des grossistes');
			} finally {
				setLoading(false);
			}
		};
		fetchWholesalers();
	}, []);

	// Charger le catalogue quand un grossiste est sélectionné ou filtres changent
	useEffect(() => {
		if (!selectedWholesaler || view !== 'products') return;

		const fetchCatalog = async () => {
			try {
				setLoading(true);
				setError(null);
				const response = await getWholesalerCatalog(selectedWholesaler.id, {
					category_id: selectedCategory,
					page: pagination.page,
				});
				if (response.success) {
					setProducts(response.data?.products || []);
					setCategories(response.data?.categories || []);
					if (response.data?.pagination) {
						setPagination(prev => ({
							...prev,
							total_products: response.data.pagination.total_products,
							total_pages: response.data.pagination.total_pages,
							page_size: response.data.pagination.page_size,
						}));
					}
				} else {
					setError(response.error?.message || 'Erreur lors du chargement du catalogue');
				}
			} catch (err) {
				setError(err.response?.data?.error?.message || 'Erreur lors du chargement du catalogue');
			} finally {
				setLoading(false);
			}
		};

		fetchCatalog();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [selectedWholesaler?.id, view, selectedCategory, pagination.page]);

	const handleSelectWholesaler = (wholesaler) => {
		setSelectedWholesaler(wholesaler);
		setPagination({ page: 1, total_products: 0, total_pages: 1 });
		setSelectedCategory(null);
		setView('products'); // Aller directement aux produits
		setCart([]); // Réinitialiser le panier pour ce nouveau grossiste
	};

	const handleAddToCart = (product, quantity) => {
		const existingItem = cart.find((item) => item.id === product.id);

		if (existingItem) {
			setCart(
				cart.map((item) =>
					item.id === product.id ? { ...item, quantity: item.quantity + quantity } : item
				)
			);
		} else {
			setCart([
				...cart,
				{
					...product,
					quantity,
					b2b_price: product.b2b_price || product.b2b_pricings?.[0]?.b2b_price,
				},
			]);
		}
	};

	const handleRemoveFromCart = (productId) => {
		setCart(cart.filter((item) => item.id !== productId));
	};

	const handleUpdateQuantity = (productId, newQuantity) => {
		if (newQuantity <= 0) {
			handleRemoveFromCart(productId);
			return;
		}

		setCart(
			cart.map((item) => (item.id === productId ? { ...item, quantity: newQuantity } : item))
		);
	};

	const handleCheckout = () => {
		if (cart.length === 0) return;
		if (view === 'products') {
			setView('cart');
		} else {
			setView('checkout');
		}
	};

	const handleSubmitOrder = async (orderData) => {
		try {
			setLoading(true);
			setError(null);
			const response = await createB2BOrder(orderData);
			if (response.success) {
				alert('Commande B2B créée avec succès !');
				setCart([]);
				setView('list');
				setSelectedWholesaler(null);
			} else {
				setError(response.error?.message || 'Erreur lors de la création de la commande');
			}
		} catch (err) {
			setError(err.response?.data?.error?.message || 'Erreur lors de la création de la commande');
		} finally {
			setLoading(false);
		}
	};

	const handleBack = () => {
		if (view === 'products') {
			setView('list');
			setSelectedWholesaler(null);
		} else if (view === 'cart') {
			setView('products');
		} else if (view === 'checkout') {
			setView('cart');
		}
	};

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="bg-white rounded-lg p-6 shadow-md border-l-4 border-indigo-600">
				<h2 className="text-2xl font-bold text-gray-900">Espace Approvisionnement B2B</h2>
				<p className="text-gray-600 mt-2">
					Accédez aux catalogues exclusifs des grossistes et industries partenaires pour réapprovisionner votre stock.
				</p>
			</div>

			{error && (
				<div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
					{error}
				</div>
			)}

			{/* Navigation */}
			{view !== 'list' && (
				<div className="mb-4">
					<button
						onClick={handleBack}
						className="text-indigo-600 hover:text-indigo-700 flex items-center gap-2 font-medium"
					>
						<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								strokeLinecap="round"
								strokeLinejoin="round"
								strokeWidth={2}
								d="M15 19l-7-7 7-7"
							/>
						</svg>
						Retour
					</button>
				</div>
			)}

			{/* Vue liste des grossistes */}
			{view === 'list' && (
				<div>
					<WholesalerList
						wholesalers={wholesalers}
						onSelectWholesaler={handleSelectWholesaler}
						loading={loading}
					/>
				</div>
			)}

			{/* Vue produits (Catalogue) */}
			{view === 'products' && selectedWholesaler && (
				<div className="space-y-6">
					{/* Header Grossiste */}
					<div className="bg-white rounded-lg shadow p-4 flex flex-col md:flex-row items-center gap-4">
						<div className="h-16 w-16 rounded-full overflow-hidden bg-gray-100 border flex-shrink-0">
							{selectedWholesaler.logo ? (
								<img src={selectedWholesaler.logo} alt="Logo" className="w-full h-full object-cover" />
							) : (
								<div className="w-full h-full flex items-center justify-center text-indigo-600 font-bold text-xl">
									{selectedWholesaler.name.charAt(0)}
								</div>
							)}
						</div>
						<div className="flex-1 text-center md:text-left">
							<h3 className="text-xl font-bold">{selectedWholesaler.name}</h3>
							<p className="text-sm text-gray-500">{selectedWholesaler.zone} • {selectedWholesaler.city || 'Libreville'}</p>
						</div>
						<div className="flex flex-col items-end gap-1">
							{(() => {
								const minAmount = selectedWholesaler.minimum_order_amount || selectedWholesaler.b2b_profile?.minimum_order_amount;
								return minAmount ? (
									<div className="text-xs font-semibold px-2 py-1 bg-blue-100 text-blue-800 rounded">
										Minimum commande: {minAmount.toLocaleString()} FCFA
									</div>
								) : null;
							})()}
							<div className="text-xs text-gray-500">
								{pagination.total_products || 0} produits disponibles
							</div>
						</div>
					</div>

					<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
						<div className="lg:col-span-2">
							{/* Filtres & Recherche */}
							<div className="mb-4 bg-white p-4 rounded-lg shadow flex flex-col md:flex-row items-center gap-4">
								<div className="flex-1 w-full">
									<input
										type="text"
										placeholder="Rechercher un produit..."
										className="w-full border border-gray-300 rounded px-3 py-2"
										onChange={() => {
											// TODO: Implémenter la recherche
										}}
									/>
								</div>
								{categories.length > 0 && (
									<div className="w-full md:w-auto">
										<select
											value={selectedCategory || ''}
											onChange={(e) => {
												setSelectedCategory(e.target.value || null);
												setPagination(prev => ({ ...prev, page: 1 }));
											}}
											className="w-full border border-gray-300 rounded px-3 py-2"
										>
											<option value="">Toutes les catégories</option>
											{categories.map((cat) => (
												<option key={cat.id} value={cat.id}>
													{cat.name} ({cat.product_count || 0})
												</option>
											))}
										</select>
									</div>
								)}
							</div>

							<B2BProductList
								products={products}
								onAddToCart={handleAddToCart}
								loading={loading}
							/>

							{/* Pagination */}
							{pagination.total_pages > 1 && (
								<div className="mt-8 flex justify-center gap-2">
									{[...Array(pagination.total_pages)].map((_, i) => (
										<button
											key={i}
											onClick={() => setPagination(prev => ({ ...prev, page: i + 1 }))}
											className={`px-4 py-2 rounded ${
												pagination.page === i + 1
													? 'bg-indigo-600 text-white'
													: 'bg-white text-gray-700 border hover:bg-gray-50'
											}`}
										>
											{i + 1}
										</button>
									))}
								</div>
							)}
						</div>

						<div className="lg:col-span-1">
							<div className="sticky top-4">
								<B2BCart
									cartItems={cart}
									onRemoveItem={handleRemoveFromCart}
									onUpdateQuantity={handleUpdateQuantity}
									onCheckout={handleCheckout}
									loading={loading}
								/>
							</div>
						</div>
					</div>
				</div>
			)}

			{/* Vue panier */}
			{view === 'cart' && selectedWholesaler && (
				<div className="max-w-4xl mx-auto">
					<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
						<div className="lg:col-span-2">
							<h3 className="text-xl font-bold mb-4">Votre panier</h3>
							<B2BCart
								cartItems={cart}
								onRemoveItem={handleRemoveFromCart}
								onUpdateQuantity={handleUpdateQuantity}
								onCheckout={handleCheckout}
								loading={loading}
							/>
						</div>
					</div>
				</div>
			)}

			{/* Vue checkout */}
			{view === 'checkout' && selectedWholesaler && (
				<div className="max-w-2xl mx-auto">
					<B2BOrderForm
						wholesaler={selectedWholesaler}
						cartItems={cart}
						onSubmit={handleSubmitOrder}
						onCancel={() => setView('cart')}
						loading={loading}
					/>
				</div>
			)}
		</div>
	);
};

export default B2BProcurementEmbedded;

