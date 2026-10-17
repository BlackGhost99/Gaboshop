import React, { useEffect, useState, useCallback } from 'react';
import StoreLayout from '../../components/StoreLayout';
import { notifySuccess, notifyError, notifyWarning } from '../../utils/feedback';
import { formatCurrency } from '../../utils/helpers';
import {
	getMyWholesalePricing,
	addMyWholesalePrice,
	updateMyWholesalePrice,
	deleteMyWholesalePrice,
} from '../../services/b2bService';

// Prix de gros du grossiste : un prix de base (avec quantité minimale) par produit, puis des paliers de quantité
// moins chers (prix dégressifs, outil du forfait). Le serveur applique le bon prix à chaque commande.

const inputClass = 'w-full border border-gray-300 rounded px-3 py-2 text-sm';

const ProductPricing = ({ product, bulk, bulkMessage, onChange }) => {
	const [basePrice, setBasePrice] = useState(product.base ? String(product.base.b2b_price) : '');
	const [baseQuantity, setBaseQuantity] = useState(product.base ? String(product.base.min_quantity) : '1');
	const [tierQuantity, setTierQuantity] = useState('');
	const [tierPrice, setTierPrice] = useState('');
	const [busy, setBusy] = useState(false);
	const [confirmRemove, setConfirmRemove] = useState(false);

	useEffect(() => {
		setBasePrice(product.base ? String(product.base.b2b_price) : '');
		setBaseQuantity(product.base ? String(product.base.min_quantity) : '1');
	}, [product.base]);

	const run = async (action, fallbackTitle, success) => {
		setBusy(true);
		try {
			const res = await action();
			if (res?.success) {
				notifySuccess(success || res.message || 'Prix enregistré');
				onChange(res.data?.product);
				return true;
			}
		} catch (err) {
			notifyError(err, { action: fallbackTitle });
		} finally {
			setBusy(false);
		}
		return false;
	};

	const saveBase = () => {
		if (!basePrice || Number(basePrice) <= 0) {
			notifyWarning('Prix de gros manquant', 'Indiquez le prix unitaire que paiera un commerce.');
			return;
		}
		if (product.base) {
			run(() => updateMyWholesalePrice(product.base.id, { b2b_price: basePrice, min_quantity: baseQuantity }),
				'Modifier le prix de gros', 'Prix de gros mis à jour');
		} else {
			run(() => addMyWholesalePrice({ product_id: product.id, b2b_price: basePrice, min_quantity: baseQuantity }),
				'Mettre en vente en gros', 'Produit mis en vente en gros');
		}
	};

	const addTier = async () => {
		if (!tierQuantity || !tierPrice) {
			notifyWarning('Palier incomplet', 'Indiquez la quantité à partir de laquelle le prix baisse, et le nouveau prix unitaire.');
			return;
		}
		const ok = await run(() => addMyWholesalePrice({ product_id: product.id, b2b_price: tierPrice, min_quantity: tierQuantity }),
			'Ajouter un palier', 'Palier ajouté');
		if (ok) {
			setTierQuantity('');
			setTierPrice('');
		}
	};

	const removeTier = (tier) => run(() => deleteMyWholesalePrice(tier.id), 'Supprimer le palier', 'Palier supprimé');

	const removeProduct = async () => {
		const ok = await run(() => deleteMyWholesalePrice(product.base.id), 'Retirer de la vente en gros', 'Produit retiré de la vente en gros');
		if (ok) setConfirmRemove(false);
	};

	const toggleTier = (tier) => run(() => updateMyWholesalePrice(tier.id, { is_active: !tier.is_active }),
		'Modifier le palier', tier.is_active ? 'Palier désactivé' : 'Palier réactivé');

	return (
		<div className="bg-white rounded-lg shadow p-4 sm:p-5">
			<div className="flex flex-wrap items-start justify-between gap-2 mb-3">
				<div className="min-w-0">
					<h3 className="font-bold text-gray-900 break-words">{product.name}</h3>
					<p className="text-xs text-gray-500">
						Prix en boutique : {formatCurrency(product.price)} · Stock : {product.stock}
					</p>
				</div>
				{product.base ? (
					<span className="text-xs font-semibold px-2 py-1 rounded bg-green-100 text-green-800">En vente en gros</span>
				) : (
					<span className="text-xs font-semibold px-2 py-1 rounded bg-gray-100 text-gray-700">Pas encore en gros</span>
				)}
			</div>

			<div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
				<div>
					<label className="block text-xs font-semibold text-gray-700 mb-1">Prix de gros (FCFA, l'unité)</label>
					<input type="number" min="1" className={inputClass} value={basePrice} onChange={(e) => setBasePrice(e.target.value)} />
				</div>
				<div>
					<label className="block text-xs font-semibold text-gray-700 mb-1">Quantité minimale</label>
					<input type="number" min="1" className={inputClass} value={baseQuantity} onChange={(e) => setBaseQuantity(e.target.value)} />
				</div>
				<button type="button" onClick={saveBase} disabled={busy}
					className="px-4 py-2 rounded bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
					{product.base ? 'Enregistrer' : 'Mettre en vente en gros'}
				</button>
			</div>

			{product.base && (
				<div className="mt-4 border-t pt-4">
					<p className="text-sm font-bold text-gray-900 mb-2">Prix dégressifs</p>

					{!bulk && (
						<p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded px-3 py-2 mb-3 break-words">
							{bulkMessage}
						</p>
					)}
					{!bulk && product.tiers.length > 0 && (
						<p className="text-xs text-gray-600 mb-3">
							Vos paliers enregistrés ne s'appliquent pas tant que votre forfait ne les inclut pas : vos acheteurs paient le prix de base.
						</p>
					)}

					{product.tiers.length === 0 ? (
						<p className="text-xs text-gray-500 mb-3">Aucun palier : tous vos acheteurs paient le prix de base.</p>
					) : (
						<ul className="space-y-2 mb-3">
							{product.tiers.map((tier) => (
								<li key={tier.id} className="flex flex-wrap items-center justify-between gap-2 text-sm bg-indigo-50 rounded px-3 py-2">
									<span className={tier.is_active && bulk ? 'text-indigo-900 font-semibold' : 'text-gray-500'}>
										Dès {tier.min_quantity} unités : {formatCurrency(tier.b2b_price)} l'unité
										{tier.saving_percent > 0 && ` (-${tier.saving_percent} %)`}
										{!tier.is_active && ' · désactivé'}
									</span>
									<span className="flex gap-3">
										{bulk && (
											<button type="button" disabled={busy} onClick={() => toggleTier(tier)}
												className="text-xs text-indigo-700 underline disabled:opacity-50">
												{tier.is_active ? 'Désactiver' : 'Réactiver'}
											</button>
										)}
										<button type="button" disabled={busy} onClick={() => removeTier(tier)}
											className="text-xs text-red-700 underline disabled:opacity-50">
											Supprimer
										</button>
									</span>
								</li>
							))}
						</ul>
					)}

					{bulk && (
						<div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
							<div>
								<label className="block text-xs font-semibold text-gray-700 mb-1">À partir de (unités)</label>
								<input type="number" min="2" className={inputClass} value={tierQuantity} onChange={(e) => setTierQuantity(e.target.value)} />
							</div>
							<div>
								<label className="block text-xs font-semibold text-gray-700 mb-1">Prix de l'unité (FCFA)</label>
								<input type="number" min="1" className={inputClass} value={tierPrice} onChange={(e) => setTierPrice(e.target.value)} />
							</div>
							<button type="button" onClick={addTier} disabled={busy}
								className="px-4 py-2 rounded border border-indigo-600 text-indigo-700 text-sm font-semibold hover:bg-indigo-50 disabled:opacity-50">
								Ajouter un palier
							</button>
						</div>
					)}

					<div className="mt-4">
						{confirmRemove ? (
							<span className="text-xs text-gray-700">
								Retirer ce produit de la vente en gros supprime aussi ses paliers.{' '}
								<button type="button" disabled={busy} onClick={removeProduct} className="text-red-700 font-semibold underline">Confirmer le retrait</button>{' '}
								<button type="button" onClick={() => setConfirmRemove(false)} className="text-gray-600 underline">Annuler</button>
							</span>
						) : (
							<button type="button" onClick={() => setConfirmRemove(true)} className="text-xs text-red-700 underline">
								Retirer de la vente en gros
							</button>
						)}
					</div>
				</div>
			)}
		</div>
	);
};

const WholesalePricing = () => {
	const [data, setData] = useState(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState('');
	const [search, setSearch] = useState('');

	const load = useCallback(async () => {
		try {
			setLoading(true);
			setError('');
			const res = await getMyWholesalePricing();
			if (res?.success) setData(res.data);
			else setError(res?.error?.message || 'Impossible de charger vos prix de gros.');
		} catch (err) {
			setError(err.response?.data?.error?.message || 'Impossible de charger vos prix de gros.');
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		load();
	}, [load]);

	const replaceProduct = (updated) => {
		if (!updated) return;
		setData((prev) => ({ ...prev, products: prev.products.map((p) => (p.id === updated.id ? updated : p)) }));
	};

	const products = (data?.products || []).filter((p) => p.name.toLowerCase().includes(search.trim().toLowerCase()));

	return (
		<StoreLayout title="Prix de gros">
			<p className="text-sm text-gray-600 mb-4">
				Fixez le prix de gros de vos produits et la quantité minimale de commande. Avec les prix dégressifs, le prix de l'unité
				baisse à partir de certaines quantités ; vos acheteurs voient les paliers dans votre catalogue et le prix exact est
				calculé à la commande.
			</p>

			{error && <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">{error}</div>}
			{loading && <p className="text-gray-600">Chargement…</p>}

			{data && (
				<>
					{!data.bulk_discounts && (
						<div className="mb-4 bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 rounded text-sm break-words">
							{data.bulk_discounts_message}
						</div>
					)}
					<input type="search" placeholder="Rechercher un produit…" className={`${inputClass} mb-4 max-w-md`}
						value={search} onChange={(e) => setSearch(e.target.value)} />
					{products.length === 0 ? (
						<p className="text-gray-600">Aucun produit à afficher. Ajoutez d'abord des produits dans « Produits ».</p>
					) : (
						<div className="space-y-4">
							{products.map((product) => (
								<ProductPricing key={product.id} product={product} bulk={data.bulk_discounts}
									bulkMessage={data.bulk_discounts_message} onChange={replaceProduct} />
							))}
						</div>
					)}
				</>
			)}
		</StoreLayout>
	);
};

export default WholesalePricing;
