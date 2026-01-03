import React, { useState } from 'react';

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

	const handleChange = (e) => {
		const { name, value } = e.target;
		setFormData((prev) => ({
			...prev,
			[name]: value,
		}));
	};

	const handleSubmit = (e) => {
		e.preventDefault();
		
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
		<form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-4">
			<h2 className="text-xl font-bold mb-4">Informations de livraison</h2>

			{/* Type de livraison */}
			<div>
				<label className="block text-sm font-semibold mb-2">Type de livraison</label>
				<select
					name="delivery_type"
					value={formData.delivery_type}
					onChange={handleChange}
					className="w-full border border-gray-300 rounded px-3 py-2"
					required
				>
					<option value="standard">Standard (2-3h)</option>
					<option value="express">Express (1h)</option>
				</select>
			</div>

			{/* Adresse */}
			<div>
				<label className="block text-sm font-semibold mb-2">Adresse de livraison *</label>
				<textarea
					name="delivery_address"
					value={formData.delivery_address}
					onChange={handleChange}
					className="w-full border border-gray-300 rounded px-3 py-2"
					rows={3}
					required
					placeholder="Adresse complète"
				/>
			</div>

			{/* Zone */}
			<div>
				<label className="block text-sm font-semibold mb-2">Zone *</label>
				<input
					type="text"
					name="delivery_zone"
					value={formData.delivery_zone}
					onChange={handleChange}
					className="w-full border border-gray-300 rounded px-3 py-2"
					required
					placeholder="Ex: Mont-Bouët, Louis, etc."
				/>
			</div>

			{/* Ville */}
			<div>
				<label className="block text-sm font-semibold mb-2">Ville</label>
				<input
					type="text"
					name="city"
					value={formData.city}
					onChange={handleChange}
					className="w-full border border-gray-300 rounded px-3 py-2"
					placeholder="Libreville"
				/>
			</div>

			{/* Téléphone */}
			<div>
				<label className="block text-sm font-semibold mb-2">Téléphone de livraison *</label>
				<input
					type="tel"
					name="delivery_phone"
					value={formData.delivery_phone}
					onChange={handleChange}
					className="w-full border border-gray-300 rounded px-3 py-2"
					required
					placeholder="+24101234567"
				/>
			</div>

			{/* Notes */}
			<div>
				<label className="block text-sm font-semibold mb-2">Notes (optionnel)</label>
				<textarea
					name="notes"
					value={formData.notes}
					onChange={handleChange}
					className="w-full border border-gray-300 rounded px-3 py-2"
					rows={3}
					placeholder="Instructions spéciales..."
				/>
			</div>

			{/* Actions */}
			<div className="flex gap-4 pt-4">
				<button
					type="button"
					onClick={onCancel}
					className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg hover:bg-gray-50 transition-colors"
				>
					Annuler
				</button>
				<button
					type="submit"
					disabled={loading}
					className="flex-1 bg-cta-600 text-white py-2 rounded-lg hover:bg-cta-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
				>
					{loading ? 'Création...' : 'Créer la commande'}
				</button>
			</div>
		</form>
	);
};

export default B2BOrderForm;

