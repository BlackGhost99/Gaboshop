import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import { getStoreDetailAdmin } from '../services/adminService';
import StoreB2BModal from './StoreB2BModal';

/**
 * Modal pour afficher les détails d'un store
 * Remplace l'alert() dans viewStoreDetail
 */
const StoreDetailModal = ({ isOpen, onClose, storeId }) => {
	const [store, setStore] = useState(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);
	const [showB2BModal, setShowB2BModal] = useState(false);

	useEffect(() => {
		if (isOpen && storeId) {
			loadStoreDetail();
		}
	}, [isOpen, storeId]);

	const loadStoreDetail = async () => {
		try {
			setLoading(true);
			setError(null);
			const res = await getStoreDetailAdmin(storeId);
			if (res?.success) {
				setStore(res.data);
			} else {
				setError('Erreur lors du chargement du magasin');
			}
		} catch (err) {
			setError(err?.message || 'Erreur lors du chargement du magasin');
		} finally {
			setLoading(false);
		}
	};

	if (!isOpen) return null;

	return (
		<>
			<Modal
				isOpen={isOpen}
				onClose={onClose}
				title={store ? `Détails - ${store.name}` : 'Détails du magasin'}
				size="lg"
			>
				{loading ? (
					<div className="text-center py-8">
						<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
						<p className="mt-2 text-sm text-gray-500">Chargement...</p>
					</div>
				) : error ? (
					<div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
						{error}
					</div>
				) : store ? (
					<div className="space-y-4">
						{/* Informations générales */}
						<div className="grid grid-cols-2 gap-4">
							<div>
								<label className="block text-sm font-semibold text-gray-700 mb-1">Nom</label>
								<p className="text-sm text-gray-900">{store.name}</p>
							</div>
							<div>
								<label className="block text-sm font-semibold text-gray-700 mb-1">Catégorie</label>
								<p className="text-sm text-gray-900">{store.category_name || '—'}</p>
							</div>
							<div>
								<label className="block text-sm font-semibold text-gray-700 mb-1">Ville</label>
								<p className="text-sm text-gray-900">{store.city || '—'}</p>
							</div>
							<div>
								<label className="block text-sm font-semibold text-gray-700 mb-1">Zone</label>
								<p className="text-sm text-gray-900">{store.zone || '—'}</p>
							</div>
							<div>
								<label className="block text-sm font-semibold text-gray-700 mb-1">Gérant</label>
								<p className="text-sm text-gray-900">{store.manager_name || '—'}</p>
							</div>
							<div>
								<label className="block text-sm font-semibold text-gray-700 mb-1">Téléphone</label>
								<p className="text-sm text-gray-900">{store.phone || '—'}</p>
							</div>
						</div>

						{/* Statuts */}
						<div className="bg-gray-50 rounded-lg p-4">
							<h4 className="text-sm font-semibold text-gray-700 mb-3">Statuts</h4>
							<div className="grid grid-cols-2 gap-3">
								<div className="flex items-center gap-2">
									<span className={`px-2 py-1 text-xs rounded-full ${store.is_active ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
										{store.is_active ? 'Actif' : 'Inactif'}
									</span>
									<span className="text-xs text-gray-600">Magasin</span>
								</div>
								<div className="flex items-center gap-2">
									<span className={`px-2 py-1 text-xs rounded-full ${store.is_b2c ? 'bg-blue-50 text-blue-700' : 'bg-gray-50 text-gray-700'}`}>
										{store.is_b2c ? 'B2C' : 'Non B2C'}
									</span>
									<span className="text-xs text-gray-600">B2C</span>
								</div>
								<div className="flex items-center gap-2">
									<span className={`px-2 py-1 text-xs rounded-full ${store.is_b2b ? 'bg-purple-50 text-purple-700' : 'bg-gray-50 text-gray-700'}`}>
										{store.is_b2b ? 'B2B' : 'Non B2B'}
									</span>
									<span className="text-xs text-gray-600">B2B</span>
								</div>
								<div className="flex items-center gap-2">
									<span className={`px-2 py-1 text-xs rounded-full ${store.is_verified ? 'bg-green-50 text-green-700' : 'bg-gray-50 text-gray-700'}`}>
										{store.is_verified ? 'Vérifié' : 'Non vérifié'}
									</span>
									<span className="text-xs text-gray-600">Vérification</span>
								</div>
							</div>
						</div>

						{/* Description */}
						{store.description && (
							<div>
								<label className="block text-sm font-semibold text-gray-700 mb-1">Description</label>
								<p className="text-sm text-gray-900 whitespace-pre-wrap">{store.description}</p>
							</div>
						)}

						{/* Actions */}
						<div className="flex gap-3 pt-4 border-t border-gray-200">
							<button
								onClick={() => setShowB2BModal(true)}
								className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-semibold"
							>
								{store.is_b2b ? 'Gérer B2B' : 'Activer B2B'}
							</button>
							<button
								onClick={onClose}
								className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
							>
								Fermer
							</button>
						</div>
					</div>
				) : null}
			</Modal>

			{/* Modal B2B */}
			{store && (
				<StoreB2BModal
					isOpen={showB2BModal}
					onClose={() => {
						setShowB2BModal(false);
						loadStoreDetail(); // Rafraîchir les détails
					}}
					store={store}
					onSuccess={() => {
						loadStoreDetail(); // Rafraîchir les détails
					}}
				/>
			)}
		</>
	);
};

export default StoreDetailModal;


