import React, { useState, useEffect } from 'react';
import { formatCurrency } from '../../utils/helpers';

/**
 * Formulaire de commande B2B
 */
const B2BOrderForm = ({ wholesaler, cartItems, onSubmit, onCancel, loading }) => {
	const [formData, setFormData] = useState({
		delivery_type: 'standard',
		notes: '',
		delivery_address: '',
		delivery_phone: '',
		delivery_zone: '',
		city: 'Libreville',
	});

	// Pré-remplir avec les données du store si disponibles
	useEffect(() => {
		// On pourrait récupérer les données du store connecté ici
		// Pour l'instant, on garde les valeurs par défaut
	}, []);

	// Calculer les totaux
	const calculateSubtotal = () => {
		return cartItems.reduce((total, item) => {
			return total + (item.b2b_price || item.price) * item.quantity;
		}, 0);
	};

	const calculateTotal = () => {
		return calculateSubtotal();
	};

	const getMinOrderAmount = () => {
		return wholesaler?.minimum_order_amount || wholesaler?.b2b_profile?.minimum_order_amount || 0;
	};

	const handleChange = (e) => {
		const { name, value } = e.target;
		setFormData((prev) => ({
			...prev,
			[name]: value,
		}));
	};

	const handleSubmit = (e) => {
		e.preventDefault();
		
		// Validation du montant minimum
		const subtotal = calculateSubtotal();
		const minAmount = getMinOrderAmount();
		if (minAmount > 0 && subtotal < minAmount) {
			alert(`Le montant minimum de commande est de ${formatCurrency(minAmount)}. Votre panier est de ${formatCurrency(subtotal)}.`);
			return;
		}

		// Validation des champs requis
		if (!formData.delivery_address?.trim()) {
			alert('Veuillez renseigner une adresse de livraison');
			return;
		}
		if (!formData.delivery_phone?.trim()) {
			alert('Veuillez renseigner un numéro de téléphone');
			return;
		}
		if (!formData.delivery_zone?.trim()) {
			alert('Veuillez renseigner une zone');
			return;
		}
		
		// Préparer les items
		const items = cartItems.map((item) => ({
			product_id: item.id,
			quantity: item.quantity,
		}));

		onSubmit?.({
			wholesaler_id: wholesaler.id,
			items,
			...formData,
		});
	};

	return (
		<div className="space-y-6">
			{/* Récapitulatif de la commande */}
			<div className="bg-white rounded-lg shadow p-6">
				<h2 className="text-xl font-bold mb-4">Récapitulatif de la commande</h2>
				
				{/* Liste des produits */}
				<div className="space-y-3 mb-4">
					{cartItems.map((item) => (
						<div key={item.id} className="flex items-center justify-between pb-3 border-b border-gray-200">
							<div className="flex items-center gap-3">
								<img
									src={item.image || '/placeholder.png'}
									alt={item.name}
									className="w-12 h-12 object-cover rounded"
									onError={(e) => { e.target.src = '/placeholder.png'; }}
								/>
								<div>
									<p className="font-bold text-sm text-black">{item.name}</p>
									<p className="text-xs text-black font-bold">
										{formatCurrency(item.b2b_price || item.price)} × {item.quantity}
									</p>
								</div>
							</div>
							<p className="font-bold text-black text-lg">
								{formatCurrency((item.b2b_price || item.price) * item.quantity)}
							</p>
						</div>
					))}
				</div>

				{/* Totaux */}
				<div className="space-y-2 pt-3 border-t-2 border-gray-400">
					<div className="flex justify-between text-sm">
						<span className="text-black font-bold">Sous-total</span>
						<span className="font-bold text-black">{formatCurrency(calculateSubtotal())}</span>
					</div>
					{getMinOrderAmount() > 0 && (
						<div className="flex justify-between text-xs">
							<span className="text-black font-bold">Minimum de commande</span>
							<span className={`font-bold ${calculateSubtotal() >= getMinOrderAmount() ? 'text-green-800' : 'text-red-800'}`}>
								{formatCurrency(getMinOrderAmount())}
							</span>
						</div>
					)}
					<div className="flex justify-between items-center pt-2 border-t-2 border-gray-400">
						<span className="text-lg font-bold text-black">Total</span>
						<span className="text-xl font-bold text-indigo-700">{formatCurrency(calculateTotal())}</span>
					</div>
				</div>
			</div>

			{/* Formulaire de livraison */}
			<form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-4">
				<h2 className="text-xl font-bold mb-4 text-black">Informations de livraison</h2>

			{/* Type de livraison */}
			<div>
				<label className="block text-sm font-bold mb-2 text-black">Type de livraison</label>
				<select
					name="delivery_type"
					value={formData.delivery_type}
					onChange={handleChange}
					className="w-full border-2 border-gray-400 rounded px-3 py-2 text-black font-semibold"
					required
				>
					<option value="standard">Standard (2-3h)</option>
					<option value="express">Express (1h)</option>
				</select>
			</div>

			{/* Adresse */}
			<div>
				<label className="block text-sm font-bold mb-2 text-black">Adresse de livraison *</label>
				<textarea
					name="delivery_address"
					value={formData.delivery_address}
					onChange={handleChange}
					className="w-full border-2 border-gray-400 rounded px-3 py-2 text-black font-medium"
					rows={3}
					required
					placeholder="Adresse complète"
				/>
			</div>

			{/* Zone */}
			<div>
				<label className="block text-sm font-bold mb-2 text-black">Zone *</label>
				<input
					type="text"
					name="delivery_zone"
					value={formData.delivery_zone}
					onChange={handleChange}
					className="w-full border-2 border-gray-400 rounded px-3 py-2 text-black font-medium"
					required
					placeholder="Ex: Mont-Bouët, Louis, etc."
				/>
			</div>

			{/* Ville */}
			<div>
				<label className="block text-sm font-bold mb-2 text-black">Ville</label>
				<input
					type="text"
					name="city"
					value={formData.city}
					onChange={handleChange}
					className="w-full border-2 border-gray-400 rounded px-3 py-2 text-black font-medium"
					placeholder="Libreville"
				/>
			</div>

			{/* Téléphone */}
			<div>
				<label className="block text-sm font-bold mb-2 text-black">Téléphone de livraison *</label>
				<input
					type="tel"
					name="delivery_phone"
					value={formData.delivery_phone}
					onChange={handleChange}
					className="w-full border-2 border-gray-400 rounded px-3 py-2 text-black font-medium"
					required
					placeholder="+24101234567"
				/>
			</div>

			{/* Notes */}
			<div>
				<label className="block text-sm font-bold mb-2 text-black">Notes (optionnel)</label>
				<textarea
					name="notes"
					value={formData.notes}
					onChange={handleChange}
					className="w-full border-2 border-gray-400 rounded px-3 py-2 text-black font-medium"
					rows={3}
					placeholder="Instructions spéciales..."
				/>
			</div>

				{/* Actions */}
				<div className="flex gap-4 pt-4">
					<button
						type="button"
						onClick={onCancel}
						className="flex-1 border-2 border-gray-500 text-black font-extrabold py-3 rounded-xl hover:bg-gray-200 transition-colors text-lg bg-white"
					>
						Retour au panier
					</button>
					<button
						type="submit"
						disabled={loading || calculateSubtotal() < getMinOrderAmount()}
						style={{ backgroundColor: '#16A34A' }}
						className="flex-1 text-white py-3 rounded-xl hover:bg-green-700 disabled:!bg-gray-400 disabled:cursor-not-allowed font-bold text-lg shadow-lg border-2 border-green-700"
					>
						{loading ? 'Création...' : calculateSubtotal() < getMinOrderAmount() ? 'Montant minimum non atteint' : 'Confirmer la commande'}
					</button>
				</div>
			</form>
		</div>
	);
};

export default B2BOrderForm;

