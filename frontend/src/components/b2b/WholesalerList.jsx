import React from 'react';
import { formatCurrency } from '../../utils/helpers';

/**
 * Liste des grossistes disponibles
 */
const WholesalerList = ({ wholesalers, onSelectWholesaler, loading }) => {
	if (loading) {
		return (
			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{[...Array(6)].map((_, i) => (
					<div key={i} className="bg-white rounded-lg shadow p-4 animate-pulse">
						<div className="h-32 bg-gray-200 rounded mb-4"></div>
						<div className="h-4 bg-gray-200 rounded mb-2"></div>
						<div className="h-4 bg-gray-200 rounded w-2/3"></div>
					</div>
				))}
			</div>
		);
	}

	if (!wholesalers || wholesalers.length === 0) {
		return (
			<div className="text-center py-12">
				<p className="text-gray-500">Aucun grossiste disponible</p>
			</div>
		);
	}

	return (
		<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{wholesalers.map((wholesaler) => (
				<div
					key={wholesaler.id}
					onClick={() => onSelectWholesaler?.(wholesaler)}
					className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow cursor-pointer overflow-hidden"
				>
					{/* Logo/Banner */}
					<div className="relative h-32 bg-gradient-to-r from-blue-500 to-blue-600">
						{wholesaler.logo ? (
							<img
								src={wholesaler.logo}
								alt={wholesaler.name}
								className="w-full h-full object-cover"
							/>
						) : (
							<div className="w-full h-full flex items-center justify-center text-white text-2xl font-bold">
								{wholesaler.name.charAt(0).toUpperCase()}
							</div>
						)}
					</div>

					{/* Content */}
					<div className="p-4">
						<h3 className="font-bold text-lg mb-2">{wholesaler.name}</h3>
						<p className="text-gray-600 text-sm mb-2">{wholesaler.zone}</p>
						
						{wholesaler.b2b_profile && (
							<div className="mt-3 pt-3 border-t border-gray-200">
								<p className="text-xs text-gray-500">
									Montant minimum: {formatCurrency(wholesaler.b2b_profile.minimum_order_amount)}
								</p>
								{wholesaler.total_products > 0 && (
									<p className="text-xs text-gray-500 mt-1">
										{wholesaler.total_products} produit(s) disponible(s)
									</p>
								)}
							</div>
						)}

						<button 
							onClick={(e) => {
								e.stopPropagation();
								onSelectWholesaler?.(wholesaler);
							}}
							className="mt-4 w-full bg-cta-600 text-white py-2 rounded-lg hover:bg-cta-700 transition-colors font-semibold"
						>
							S'approvisionner
						</button>
					</div>
				</div>
			))}
		</div>
	);
};

export default WholesalerList;

