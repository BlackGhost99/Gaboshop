import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import {
	getB2BPricingList,
	createB2BPricing,
	updateB2BPricing,
	deleteB2BPricing,
	bulkCreateB2BPricing,
} from '../services/b2bService';

/**
 * Modal pour gérer les prix B2B des produits d'un store
 */
const B2BPricingModal = ({ isOpen, onClose, store, onSuccess }) => {
	const [loading, setLoading] = useState(false);
	const [pricings, setPricings] = useState([]);
	const [productsWithoutPricing, setProductsWithoutPricing] = useState([]);
	const [error, setError] = useState(null);
	const [bulkDiscount, setBulkDiscount] = useState(10);
	const [editingPricing, setEditingPricing] = useState(null);
	const [newPricing, setNewPricing] = useState({
		product_id: '',
		b2b_price: '',
		min_quantity: 1,
		max_quantity: '',
	});

	useEffect(() => {
		if (isOpen && store) {
			loadPricings();
		}
	}, [isOpen, store]);

	const loadPricings = async () => {
		if (!store) return;

		try {
			setLoading(true);
			setError(null);
			const response = await getB2BPricingList(store.id);
			if (response.success) {
				setPricings(response.data.pricings || []);
				setProductsWithoutPricing(response.data.products_without_pricing || []);
			} else {
				setError(response.error?.message || 'Erreur lors du chargement');
			}
		} catch (err) {
			setError(err.response?.data?.error?.message || 'Erreur lors du chargement');
		} finally {
			setLoading(false);
		}
	};

	const handleBulkCreate = async () => {
		if (!store) return;

		try {
			setLoading(true);
			setError(null);
			const response = await bulkCreateB2BPricing(store.id, bulkDiscount);
			if (response.success) {
				await loadPricings();
				onSuccess?.();
			} else {
				setError(response.error?.message || 'Erreur lors de la création en masse');
			}
		} catch (err) {
			setError(err.response?.data?.error?.message || 'Erreur lors de la création en masse');
		} finally {
			setLoading(false);
		}
	};

	const handleCreatePricing = async (e) => {
		e.preventDefault();
		if (!store || !newPricing.product_id || !newPricing.b2b_price) return;

		try {
			setLoading(true);
			setError(null);
			const response = await createB2BPricing({
				store_id: store.id,
				...newPricing,
				max_quantity: newPricing.max_quantity || null,
			});
			if (response.success) {
				setNewPricing({ product_id: '', b2b_price: '', min_quantity: 1, max_quantity: '' });
				await loadPricings();
				onSuccess?.();
			} else {
				setError(response.error?.message || 'Erreur lors de la création');
			}
		} catch (err) {
			setError(err.response?.data?.error?.message || 'Erreur lors de la création');
		} finally {
			setLoading(false);
		}
	};

	const handleUpdatePricing = async () => {
		if (!editingPricing) return;

		try {
			setLoading(true);
			setError(null);
			const response = await updateB2BPricing(editingPricing.id, {
				b2b_price: editingPricing.b2b_price,
				min_quantity: editingPricing.min_quantity,
				max_quantity: editingPricing.max_quantity || null,
				is_active: editingPricing.is_active,
			});
			if (response.success) {
				setEditingPricing(null);
				await loadPricings();
				onSuccess?.();
			} else {
				setError(response.error?.message || 'Erreur lors de la mise à jour');
			}
		} catch (err) {
			setError(err.response?.data?.error?.message || 'Erreur lors de la mise à jour');
		} finally {
			setLoading(false);
		}
	};

	const handleDeletePricing = async (pricingId) => {
		if (!window.confirm('Supprimer ce prix B2B ?')) return;

		try {
			setLoading(true);
			setError(null);
			const response = await deleteB2BPricing(pricingId);
			if (response.success) {
				await loadPricings();
				onSuccess?.();
			} else {
				setError(response.error?.message || 'Erreur lors de la suppression');
			}
		} catch (err) {
			setError(err.response?.data?.error?.message || 'Erreur lors de la suppression');
		} finally {
			setLoading(false);
		}
	};

	if (!store) return null;

	return (
		<Modal
			isOpen={isOpen}
			onClose={onClose}
			title={`Prix B2B - ${store.name}`}
			size="lg"
		>
			<div className="space-y-6">
				{error && (
					<div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
						{error}
					</div>
				)}

				{/* Création en masse */}
				<div className="bg-blue-50 rounded-lg p-4">
					<h4 className="font-semibold text-blue-900 mb-3">Création rapide</h4>
					<p className="text-sm text-blue-700 mb-3">
						Créer des prix B2B pour tous les produits sans prix avec une remise automatique.
					</p>
					<div className="flex items-center gap-4">
						<div className="flex items-center gap-2">
							<label className="text-sm font-medium">Remise:</label>
							<input
								type="number"
								value={bulkDiscount}
								onChange={(e) => setBulkDiscount(parseFloat(e.target.value) || 0)}
								className="w-20 border rounded px-2 py-1 text-sm"
								min="0"
								max="100"
							/>
							<span className="text-sm">%</span>
						</div>
						<button
							onClick={handleBulkCreate}
							disabled={loading || productsWithoutPricing.length === 0}
							className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300 text-sm"
						>
							Créer pour {productsWithoutPricing.length} produit(s)
						</button>
					</div>
				</div>

				{/* Formulaire d'ajout individuel */}
				{productsWithoutPricing.length > 0 && (
					<div className="bg-gray-50 rounded-lg p-4">
						<h4 className="font-semibold mb-3">Ajouter un prix B2B</h4>
						<form onSubmit={handleCreatePricing} className="grid grid-cols-4 gap-3">
							<select
								value={newPricing.product_id}
								onChange={(e) => setNewPricing({ ...newPricing, product_id: e.target.value })}
								className="border rounded px-2 py-1 text-sm"
								required
							>
								<option value="">Sélectionner un produit</option>
								{productsWithoutPricing.map((p) => (
									<option key={p.id} value={p.id}>
										{p.name} ({p.price} FCFA)
									</option>
								))}
							</select>
							<input
								type="number"
								placeholder="Prix B2B"
								value={newPricing.b2b_price}
								onChange={(e) => setNewPricing({ ...newPricing, b2b_price: e.target.value })}
								className="border rounded px-2 py-1 text-sm"
								required
							/>
							<input
								type="number"
								placeholder="Qté min"
								value={newPricing.min_quantity}
								onChange={(e) => setNewPricing({ ...newPricing, min_quantity: parseInt(e.target.value) || 1 })}
								className="border rounded px-2 py-1 text-sm"
								min="1"
							/>
							<button
								type="submit"
								disabled={loading}
								className="px-4 py-1 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-300 text-sm"
							>
								Ajouter
							</button>
						</form>
					</div>
				)}

				{/* Liste des prix B2B existants */}
				<div>
					<h4 className="font-semibold mb-3">Prix B2B configurés ({pricings.length})</h4>
					{loading && pricings.length === 0 ? (
						<div className="text-center py-8">
							<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
						</div>
					) : pricings.length === 0 ? (
						<div className="text-center py-8 text-gray-500">
							Aucun prix B2B configuré
						</div>
					) : (
						<div className="overflow-x-auto">
							<table className="min-w-full divide-y divide-gray-200">
								<thead className="bg-gray-50">
									<tr>
										<th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Produit</th>
										<th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Prix B2B</th>
										<th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Qté Min</th>
										<th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Qté Max</th>
										<th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Actif</th>
										<th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
									</tr>
								</thead>
								<tbody className="bg-white divide-y divide-gray-200">
									{pricings.map((pricing) => (
										<tr key={pricing.id}>
											{editingPricing?.id === pricing.id ? (
												<>
													<td className="px-3 py-2 text-sm">{pricing.product_name}</td>
													<td className="px-3 py-2">
														<input
															type="number"
															value={editingPricing.b2b_price}
															onChange={(e) => setEditingPricing({ ...editingPricing, b2b_price: e.target.value })}
															className="w-24 border rounded px-2 py-1 text-sm"
														/>
													</td>
													<td className="px-3 py-2">
														<input
															type="number"
															value={editingPricing.min_quantity}
															onChange={(e) => setEditingPricing({ ...editingPricing, min_quantity: parseInt(e.target.value) || 1 })}
															className="w-16 border rounded px-2 py-1 text-sm"
														/>
													</td>
													<td className="px-3 py-2">
														<input
															type="number"
															value={editingPricing.max_quantity || ''}
															onChange={(e) => setEditingPricing({ ...editingPricing, max_quantity: e.target.value ? parseInt(e.target.value) : null })}
															className="w-16 border rounded px-2 py-1 text-sm"
															placeholder="∞"
														/>
													</td>
													<td className="px-3 py-2">
														<input
															type="checkbox"
															checked={editingPricing.is_active}
															onChange={(e) => setEditingPricing({ ...editingPricing, is_active: e.target.checked })}
														/>
													</td>
													<td className="px-3 py-2 text-right">
														<button
															onClick={handleUpdatePricing}
															className="text-green-600 hover:text-green-800 mr-2"
														>
															✓
														</button>
														<button
															onClick={() => setEditingPricing(null)}
															className="text-gray-600 hover:text-gray-800"
														>
															✗
														</button>
													</td>
												</>
											) : (
												<>
													<td className="px-3 py-2 text-sm font-medium">{pricing.product_name}</td>
													<td className="px-3 py-2 text-sm">{parseFloat(pricing.b2b_price).toLocaleString('fr-FR')} FCFA</td>
													<td className="px-3 py-2 text-sm">{pricing.min_quantity}</td>
													<td className="px-3 py-2 text-sm">{pricing.max_quantity || '∞'}</td>
													<td className="px-3 py-2">
														<span className={`px-2 py-1 text-xs rounded-full ${pricing.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
															{pricing.is_active ? 'Oui' : 'Non'}
														</span>
													</td>
													<td className="px-3 py-2 text-right">
														<button
															onClick={() => setEditingPricing({ ...pricing })}
															className="text-indigo-600 hover:text-indigo-800 mr-2"
														>
															✏️
														</button>
														<button
															onClick={() => handleDeletePricing(pricing.id)}
															className="text-red-600 hover:text-red-800"
														>
															🗑️
														</button>
													</td>
												</>
											)}
										</tr>
									))}
								</tbody>
							</table>
						</div>
					)}
				</div>

				{/* Actions */}
				<div className="flex justify-end pt-4 border-t">
					<button
						onClick={onClose}
						className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
					>
						Fermer
					</button>
				</div>
			</div>
		</Modal>
	);
};

export default B2BPricingModal;


