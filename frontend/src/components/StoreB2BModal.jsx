import React, { useState } from 'react';
import Modal from './Modal';
import { updateStoreB2BSettings } from '../services/adminService';

/**
 * Modal pour gérer les paramètres B2B d'un magasin
 */
const StoreB2BModal = ({ isOpen, onClose, store, onSuccess }) => {
	const [isB2B, setIsB2B] = useState(store?.is_b2b || false);
	const [minOrderAmount, setMinOrderAmount] = useState(store?.b2b_min_order_amount || 0);
	const [deliveryDelay, setDeliveryDelay] = useState(store?.b2b_delivery_delay || 24);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);
	const [success, setSuccess] = useState(false);

	// Mettre à jour les valeurs quand le store change
	React.useEffect(() => {
		if (store) {
			setIsB2B(store.is_b2b || false);
			setMinOrderAmount(store.b2b_min_order_amount || 0);
			setDeliveryDelay(store.b2b_delivery_delay || 24);
		}
	}, [store]);

	const handleSubmit = async (e) => {
		e.preventDefault();
		setLoading(true);
		setError(null);
		setSuccess(false);

		try {
			const res = await updateStoreB2BSettings(store.id, {
				is_b2b: isB2B,
				b2b_min_order_amount: minOrderAmount,
				b2b_delivery_delay: deliveryDelay
			});

			if (res?.success) {
				setSuccess(true);
				// Afficher un message de confirmation avec les infos du profil B2B
				if (res?.data?.b2b_profile && isB2B) {
					console.log('Profil B2B créé/activé:', res.data.b2b_profile);
				}
				if (onSuccess) {
					onSuccess();
				}
				// Fermer après 2s pour laisser le temps de voir le message
				setTimeout(() => {
					onClose();
					setSuccess(false);
				}, 2000);
			} else {
				setError(res?.error || res?.message || 'Erreur lors de la mise à jour');
			}
		} catch (err) {
			setError(err?.message || 'Erreur lors de la mise à jour');
		} finally {
			setLoading(false);
		}
	};

	if (!isOpen || !store) return null;

	return (
		<Modal
			isOpen={isOpen}
			onClose={onClose}
			title={`Paramètres B2B - ${store.name}`}
			size="md"
		>
			<form onSubmit={handleSubmit} className="space-y-4">
				{error && (
					<div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
						{error}
					</div>
				)}

				{success && (
					<div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded text-sm">
						<div className="font-semibold mb-1">✓ Paramètres B2B mis à jour avec succès</div>
						{isB2B && (
							<div className="text-xs mt-1 text-green-600">
								Le profil B2B a été créé/activé automatiquement. Le magasin est maintenant visible comme grossiste.
							</div>
						)}
					</div>
				)}

				{/* Activer B2B */}
				<div className="bg-gray-50 rounded-lg p-4">
					<label className="flex items-center gap-3 cursor-pointer">
						<input
							type="checkbox"
							checked={isB2B}
							onChange={(e) => setIsB2B(e.target.checked)}
							className="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
						/>
						<div>
							<span className="text-sm font-semibold text-gray-900">Activer le mode B2B</span>
							<p className="text-xs text-gray-600 mt-0.5">
								Permet au magasin de vendre en gros à d'autres magasins
							</p>
						</div>
					</label>
				</div>

				{/* Paramètres B2B (affichés uniquement si B2B activé) */}
				{isB2B && (
					<>
						{/* Montant minimum de commande */}
						<div>
							<label className="block text-sm font-semibold text-gray-700 mb-2">
								Montant minimum de commande (FCFA)
							</label>
							<input
								type="number"
								min="0"
								step="1"
								value={minOrderAmount}
								onChange={(e) => setMinOrderAmount(parseFloat(e.target.value) || 0)}
								className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
								placeholder="0"
							/>
							<p className="text-xs text-gray-500 mt-1">
								Montant minimum pour passer une commande B2B auprès de ce magasin
							</p>
						</div>

						{/* Délai de livraison */}
						<div>
							<label className="block text-sm font-semibold text-gray-700 mb-2">
								Délai de livraison (heures)
							</label>
							<input
								type="number"
								min="1"
								step="1"
								value={deliveryDelay}
								onChange={(e) => setDeliveryDelay(parseInt(e.target.value) || 24)}
								className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
								placeholder="24"
							/>
							<p className="text-xs text-gray-500 mt-1">
								Délai estimé pour préparer et livrer une commande B2B
							</p>
						</div>

						{/* Info supplémentaire */}
						<div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
							<p className="text-xs text-purple-800">
								<strong>Note:</strong> Les magasins B2B apparaîtront dans la section "Approvisionnement" 
								des autres magasins qui ont accès à l'espace B2B.
							</p>
						</div>
					</>
				)}

				{/* Actions */}
				<div className="flex gap-3 pt-4 border-t border-gray-200">
					<button
						type="submit"
						disabled={loading || success}
						className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
					>
						{loading ? 'Enregistrement...' : success ? '✓ Enregistré' : 'Enregistrer'}
					</button>
					<button
						type="button"
						onClick={onClose}
						disabled={loading}
						className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
					>
						Annuler
					</button>
				</div>
			</form>
		</Modal>
	);
};

export default StoreB2BModal;

