import React, { useState } from 'react';
import Modal from './Modal';
import { updateStoreB2CSettings } from '../services/adminService';

/**
 * Modal pour gérer les paramètres B2C d'un magasin
 */
const StoreB2CModal = ({ isOpen, onClose, store, onSuccess }) => {
	const [isB2C, setIsB2C] = useState(store?.is_b2c !== false);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);
	const [success, setSuccess] = useState(false);

	// Mettre à jour les valeurs quand le store change
	React.useEffect(() => {
		if (store) {
			setIsB2C(store.is_b2c !== false);
		}
	}, [store]);

	const handleSubmit = async (e) => {
		e.preventDefault();
		setLoading(true);
		setError(null);
		setSuccess(false);

		try {
			const res = await updateStoreB2CSettings(store.id, {
				is_b2c: isB2C
			});

			if (res?.success) {
				setSuccess(true);
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
			title={`Paramètres B2C - ${store.name}`}
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
						<div className="font-semibold mb-1">✓ Paramètres B2C mis à jour avec succès</div>
						{isB2C && (
							<div className="text-xs mt-1 text-green-600">
								Le magasin peut maintenant vendre au détail (B2C). Les produits seront visibles pour les clients finaux.
							</div>
						)}
					</div>
				)}

				{/* Activer B2C */}
				<div className="bg-gray-50 rounded-lg p-4">
					<label className="flex items-center gap-3 cursor-pointer">
						<input
							type="checkbox"
							checked={isB2C}
							onChange={(e) => setIsB2C(e.target.checked)}
							className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
						/>
						<div>
							<span className="text-sm font-semibold text-gray-900">Activer le mode B2C</span>
							<p className="text-xs text-gray-600 mt-0.5">
								Permet au magasin de vendre au détail aux clients finaux
							</p>
						</div>
					</label>
				</div>

				{/* Info supplémentaire */}
				{isB2C && (
					<div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
						<p className="text-xs text-blue-800">
							<strong>Note:</strong> Les produits du magasin avec <code>market_type='b2c'</code> ou <code>'both'</code> 
							seront visibles dans le catalogue client. Les clients pourront passer des commandes B2C.
						</p>
					</div>
				)}

				{!isB2C && (
					<div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
						<p className="text-xs text-yellow-800">
							<strong>Attention:</strong> Si B2C est désactivé, les produits du magasin ne seront plus visibles 
							pour les clients finaux. Le magasin ne pourra plus recevoir de commandes B2C.
						</p>
					</div>
				)}

				{/* Actions */}
				<div className="flex gap-3 pt-4 border-t border-gray-200">
					<button
						type="submit"
						disabled={loading || success}
						className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
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

export default StoreB2CModal;
