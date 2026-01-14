import React, { useState, useEffect } from 'react';
import StoreLayout from '../../components/StoreLayout';
import WholesalerList from '../../components/b2b/WholesalerList';
import WholesalerDetail from '../../components/b2b/WholesalerDetail';
import B2BProductList from '../../components/b2b/B2BProductList';
import B2BCart from '../../components/b2b/B2BCart';
import B2BOrderForm from '../../components/b2b/B2BOrderForm';
import {
	getWholesalers,
	getWholesalerDetail,
	getB2BProducts,
	getB2BCategories,
	createB2BOrder,
} from '../../services/b2bService';

/**
 * Page principale d'approvisionnement B2B
 */
const B2BProcurement = () => {
	const [view, setView] = useState('list'); // 'list', 'detail', 'products', 'cart', 'checkout'
	const [wholesalers, setWholesalers] = useState([]);
	const [selectedWholesaler, setSelectedWholesaler] = useState(null);
	const [products, setProducts] = useState([]);
	const [categories, setCategories] = useState([]);
	const [selectedCategory, setSelectedCategory] = useState(null);
	const [cart, setCart] = useState([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);

	// Charger les grossistes au montage
	useEffect(() => {
		fetchWholesalers();
	}, []);

	// Charger les produits quand un grossiste est sélectionné
	useEffect(() => {
		if (selectedWholesaler && view === 'products') {
			fetchProducts();
			fetchCategories();
		}
	}, [selectedWholesaler, view, selectedCategory]);

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

	const fetchWholesalerDetail = async (id) => {
		try {
			setLoading(true);
			setError(null);
			const response = await getWholesalerDetail(id);
			if (response.success) {
				setSelectedWholesaler(response.data);
				setView('detail');
			} else {
				setError(response.error?.message || 'Erreur lors du chargement du grossiste');
			}
		} catch (err) {
			setError(err.response?.data?.error?.message || 'Erreur lors du chargement du grossiste');
		} finally {
			setLoading(false);
		}
	};

	const fetchProducts = async () => {
		if (!selectedWholesaler) return;

		try {
			setLoading(true);
			setError(null);
			const response = await getB2BProducts(selectedWholesaler.id, {
				category_id: selectedCategory,
			});
			if (response.success) {
				setProducts(response.data?.products || []);
			} else {
				setError(response.error?.message || 'Erreur lors du chargement des produits');
			}
		} catch (err) {
			setError(err.response?.data?.error?.message || 'Erreur lors du chargement des produits');
		} finally {
			setLoading(false);
		}
	};

	const fetchCategories = async () => {
		if (!selectedWholesaler) return;

		try {
			const response = await getB2BCategories(selectedWholesaler.id);
			if (response.success) {
				setCategories(response.data || []);
			}
		} catch (err) {
			console.error('Erreur lors du chargement des catégories:', err);
		}
	};

	const handleSelectWholesaler = (wholesaler) => {
		setSelectedWholesaler(wholesaler);
		setView('detail');
	};

	const handleViewProducts = (wholesaler) => {
		setSelectedWholesaler(wholesaler);
		setView('products');
		setCart([]); // Réinitialiser le panier
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
		// Si on est sur la vue produits, aller au panier d'abord
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
				// Succès - rediriger ou afficher un message
				alert('Commande B2B créée avec succès !');
				setCart([]);
				setView('list');
				fetchWholesalers(); // Rafraîchir la liste
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
		if (view === 'detail') {
			setView('list');
			setSelectedWholesaler(null);
		} else if (view === 'products') {
			setView('detail');
		} else if (view === 'cart') {
			setView('products');
		} else if (view === 'checkout') {
			setView('cart');
		}
	};

	// Ajouter un bouton pour voir le panier depuis la vue produits
	const handleViewCart = () => {
		if (cart.length > 0) {
			setView('cart');
		}
	};

	return (
		<StoreLayout title="Approvisionnement (B2B)">
			{error && (
				<div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
					{error}
				</div>
			)}

			{/* Navigation */}
			{view !== 'list' && (
				<div className="mb-4">
					<button
						onClick={handleBack}
						className="text-cta-600 hover:text-cta-700 flex items-center gap-2"
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
					<h3 className="text-xl font-bold mb-4">Grossistes disponibles</h3>
					<WholesalerList
						wholesalers={wholesalers}
						onSelectWholesaler={handleSelectWholesaler}
						loading={loading}
					/>
				</div>
			)}

			{/* Vue détails du grossiste */}
			{view === 'detail' && selectedWholesaler && (
				<div>
					<WholesalerDetail
						wholesaler={selectedWholesaler}
						onViewProducts={handleViewProducts}
						loading={loading}
					/>
				</div>
			)}

			{/* Vue produits */}
			{view === 'products' && selectedWholesaler && (
				<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
					<div className="lg:col-span-2">
						{/* Filtres */}
						<div className="mb-4 flex items-center gap-4">
							<h3 className="text-xl font-bold">Produits disponibles</h3>
							{categories.length > 0 && (
								<select
									value={selectedCategory || ''}
									onChange={(e) => setSelectedCategory(e.target.value || null)}
									className="border border-gray-300 rounded px-3 py-2"
								>
									<option value="">Toutes les catégories</option>
									{categories.map((cat) => (
										<option key={cat.id} value={cat.id}>
											{cat.name}
										</option>
									))}
								</select>
							)}
						</div>

						<B2BProductList
							products={products}
							onAddToCart={handleAddToCart}
							loading={loading}
						/>
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
		</StoreLayout>
	);
};

export default B2BProcurement;

