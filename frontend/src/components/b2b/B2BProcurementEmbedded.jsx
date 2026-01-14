import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import WholesalerList from './WholesalerList';
import WholesalerDetail from './WholesalerDetail';
import B2BProductList from './B2BProductList';
import B2BCart from './B2BCart';
import B2BCartSummary from './B2BCartSummary';
import B2BOrderForm from './B2BOrderForm';
import LoadingSpinner from '../LoadingSpinner';
import Modal from '../Modal';
import {
	getWholesalers,
	getWholesalerCatalog,
	createB2BOrder,
} from '../../services/b2bService';

/**
 * Composant d'approvisionnement B2B intégré dans le dashboard
 * (sans StoreLayout car déjà géré par le parent)
 */
const B2BProcurementEmbedded = ({ subscription, store }) => {
	const [view, setView] = useState('list'); // 'list', 'detail', 'products', 'cart', 'checkout'
	const [wholesalers, setWholesalers] = useState([]);
	const [selectedWholesaler, setSelectedWholesaler] = useState(null);
	const [products, setProducts] = useState([]);
	const [categories, setCategories] = useState([]);
	const [selectedCategory, setSelectedCategory] = useState(null);
	const [cart, setCart] = useState([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);
	const [successModal, setSuccessModal] = useState({ isOpen: false, message: '' });
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

		const item = cart.find((item) => item.id === productId);
		if (!item) return;

		// Valider la quantité minimale
		const minQuantity = item.min_order_quantity || 1;
		const finalQuantity = Math.max(newQuantity, minQuantity);

		// Vérifier le stock
		if (item.stock < finalQuantity) {
			setError(`Stock insuffisant. Disponible: ${item.stock} unité(s)`);
			return;
		}

		setCart(
			cart.map((item) => (item.id === productId ? { ...item, quantity: finalQuantity } : item))
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
				setSuccessModal({
					isOpen: true,
					message: `Commande B2B créée avec succès !\n\nNuméro de commande: ${response.data?.order_number || 'N/A'}`
				});
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

	// Vérifier si le plan est Free B2B
	const isB2BFree = subscription?.plan_type === 'free' && store?.is_b2b;

	if (isB2BFree) {
		return (
			<div className="bg-white rounded-2xl shadow-lg p-8 border border-gray-200">
				<div className="flex flex-col items-center justify-center text-center py-12">
					<div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mb-6">
						<svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
						</svg>
					</div>
					<h3 className="text-2xl font-bold text-gray-900 mb-3">Fonctionnalité non disponible</h3>
					<p className="text-gray-600 mb-2 max-w-md">
						L'approvisionnement B2B n'est pas disponible avec le plan <strong>Free</strong>.
					</p>
					<p className="text-gray-600 mb-6 max-w-md">
						Passez au plan <strong>Pro</strong> ou <strong>Business</strong> pour accéder aux catalogues exclusifs des grossistes et industries partenaires.
					</p>
					<Link
						to="/store/subscription"
						className="inline-flex items-center px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors"
					>
						<svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
						</svg>
						Voir les plans disponibles
					</Link>
				</div>
			</div>
		);
	}

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="bg-white rounded-lg p-6 shadow-md border-l-4 border-indigo-600">
				<h2 className="text-2xl font-bold text-gray-900">Espace Approvisionnement B2B</h2>
				<p className="text-black mt-2 font-medium">
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
							<h3 className="text-xl font-bold text-black">{selectedWholesaler.name}</h3>
							<p className="text-sm text-black font-bold">{selectedWholesaler.zone} • {selectedWholesaler.city || 'Libreville'}</p>
						</div>
						<div className="flex flex-col items-end gap-1">
							{(() => {
								const minAmount = selectedWholesaler.minimum_order_amount || selectedWholesaler.b2b_profile?.minimum_order_amount;
								return minAmount ? (
									<div className="text-xs font-bold px-2 py-1 bg-blue-200 text-black rounded border-2 border-blue-400">
										Minimum commande: {minAmount.toLocaleString()} FCFA
									</div>
								) : null;
							})()}
							<div className="text-xs text-black font-bold">
								{pagination.total_products || 0} produits disponibles
							</div>
						</div>
					</div>

					{/* Cart Summary */}
					<div className="mb-6">
						<B2BCartSummary
							cartItems={cart}
							onViewCart={() => setView('cart')}
						/>
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
									wholesaler={selectedWholesaler}
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
								wholesaler={selectedWholesaler}
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

			{/* Modal de succès */}
			<Modal
				isOpen={successModal.isOpen}
				onClose={() => setSuccessModal({ isOpen: false, message: '' })}
				title="Commande créée avec succès"
				onConfirm={() => setSuccessModal({ isOpen: false, message: '' })}
				confirmText="OK"
				showCancel={false}
				confirmButtonClass="bg-green-600 hover:bg-green-700"
			>
				<div className="text-center py-4">
					<div className="mb-4">
						<svg className="mx-auto h-16 w-16 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
					</div>
					<p className="text-gray-700 whitespace-pre-line">{successModal.message}</p>
				</div>
			</Modal>
		</div>
	);
};

export default B2BProcurementEmbedded;

