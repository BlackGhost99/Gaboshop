import React from 'react';
import { formatCurrency } from '../../utils/helpers';

/**
 * Détails d'un grossiste
 */
const WholesalerDetail = ({ wholesaler, onViewProducts, loading }) => {
	if (loading) {
		return (
			<div className="bg-white rounded-lg shadow p-6 animate-pulse">
				<div className="h-48 bg-gray-200 rounded mb-4"></div>
				<div className="h-6 bg-gray-200 rounded mb-2"></div>
				<div className="h-4 bg-gray-200 rounded w-2/3"></div>
			</div>
		);
	}

	if (!wholesaler) {
		return (
			<div className="bg-white rounded-lg shadow p-6 text-center">
				<p className="text-gray-500">Grossiste non trouvé</p>
			</div>
		);
	}

	return (
		<div className="bg-white rounded-lg shadow overflow-hidden">
			{/* Banner */}
			<div className="relative h-48 bg-gradient-to-r from-blue-500 to-blue-600">
				{wholesaler.banner_image ? (
					<img
						src={wholesaler.banner_image}
						alt={wholesaler.name}
						className="w-full h-full object-cover"
					/>
				) : wholesaler.logo ? (
					<div className="w-full h-full flex items-center justify-center">
						<img
							src={wholesaler.logo}
							alt={wholesaler.name}
							className="h-32 w-32 rounded-full object-cover border-4 border-white"
						/>
					</div>
				) : null}
			</div>

			{/* Content */}
			<div className="p-6">
				<h2 className="text-2xl font-bold mb-2">{wholesaler.name}</h2>
				<p className="text-gray-600 mb-4">{wholesaler.description || 'Aucune description'}</p>

				{/* Informations */}
				<div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
					<div>
						<p className="text-sm text-gray-500">Zone</p>
						<p className="font-semibold">{wholesaler.zone}</p>
					</div>
					<div>
						<p className="text-sm text-gray-500">Ville</p>
						<p className="font-semibold">{wholesaler.city || 'Libreville'}</p>
					</div>
					<div>
						<p className="text-sm text-gray-500">Téléphone</p>
						<p className="font-semibold">{wholesaler.phone}</p>
					</div>
					{wholesaler.email && (
						<div>
							<p className="text-sm text-gray-500">Email</p>
							<p className="font-semibold">{wholesaler.email}</p>
						</div>
					)}
				</div>

				{/* Conditions B2B */}
				{wholesaler.b2b_profile && (
					<div className="bg-blue-50 rounded-lg p-4 mb-6">
						<h3 className="font-bold mb-3">Conditions B2B</h3>
						<div className="space-y-2">
							<p className="text-sm">
								<span className="font-semibold">Montant minimum:</span>{' '}
								{formatCurrency(wholesaler.b2b_profile.minimum_order_amount)}
							</p>
							{wholesaler.total_products > 0 && (
								<p className="text-sm">
									<span className="font-semibold">Produits disponibles:</span>{' '}
									{wholesaler.total_products}
								</p>
							)}
						</div>
					</div>
				)}

				{/* Actions */}
				<button
					onClick={() => onViewProducts?.(wholesaler)}
					className="w-full bg-cta-600 text-white py-3 rounded-lg hover:bg-cta-700 transition-colors font-semibold"
				>
					Voir les produits disponibles
				</button>
			</div>
		</div>
	);
};

export default WholesalerDetail;

