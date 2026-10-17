import React from 'react';

/**
 * Prévient l'acheteur, avant qu'il remplisse son panier, que ce grossiste n'accepte plus de nouveaux commerces clients.
 * Un commerce déjà client n'est jamais concerné (le serveur envoie alors accepts_new_buyers = true).
 */
const B2BBuyerCapNotice = ({ info }) => {
	if (!info || info.accepts_new_buyers !== false) return null;
	return (
		<div className="mb-4 bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 rounded text-sm" role="status">
			{info.buyer_cap_message || 'Ce grossiste ne peut plus accepter de nouveaux commerces clients pour le moment.'}
			{' '}Vous pouvez consulter son catalogue, mais votre commande serait refusée.
		</div>
	);
};

export default B2BBuyerCapNotice;
