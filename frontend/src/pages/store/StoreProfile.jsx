import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { notifyError, notifySuccess, notifyWarning } from '../../utils/feedback';
import StoreLayout from '../../components/StoreLayout';
import { getStoreDashboard } from '../../services/dashboardService';
import { getStoreDetails, updateStore } from '../../services/storeService';

// Opérateur du numéro de versement, déduit de son début : 07… Airtel Money, 06… Moov Money.
const payoutOperatorText = (phone) => {
    const digits = (phone || '').replace(/\D/g, '').replace(/^241(?=\d{8}$)/, '');
    const local = digits.length === 8 ? `0${digits}` : digits;
    if (!local) return 'Numéro Airtel (074, 076, 077) ou Moov (060, 062, 065, 066).';
    if (local.startsWith('07')) return 'Airtel Money';
    if (local.startsWith('06')) return 'Moov Money';
    return 'Numéro Airtel (07…) ou Moov (06…) uniquement.';
};

// Seuil des alertes de stock : nombre entier de 0 à 1000 (même limite que le serveur).
const STOCK_ALERT_MAX = 1000;
const normalizeThreshold = (raw) => {
    if (raw === '' || raw === null || raw === undefined) return '';
    const n = Number(raw);
    if (!Number.isFinite(n)) return '';
    return String(Math.min(STOCK_ALERT_MAX, Math.max(0, Math.trunc(n))));
};
// Pas de virgule, de signe ni d'exposant : seulement des unités entières.
const blockNonInteger = (e) => {
    if (['.', ',', 'e', 'E', '-', '+'].includes(e.key)) e.preventDefault();
};

// Noms des champs en clair dans les erreurs renvoyées par le serveur.
const FIELD_NAMES = {
    stock_alert_threshold: "Seuil d'alerte de stock",
    agent_code: 'Code agent',
    payout_phone: 'Numéro Mobile Money',
    delivery_fee: 'Frais de livraison',
    min_order_amount: 'Montant min. commande',
    opening_time: "Heure d'ouverture",
    closing_time: 'Heure de fermeture',
    offers_delivery: 'Livraison',
    banner_image: 'Bannière',
    logo: 'Logo',
};
const withFieldNames = (details) => Object.fromEntries(
    Object.entries(details).map(([key, value]) => [FIELD_NAMES[key] || key, value])
);

const StoreProfile = () => {
    const [store, setStore] = useState(null);
    const [loading, setLoading] = useState(true);
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        phone: '',
        email: '',
        address: '',
        zone: '',
        opening_time: '',
        closing_time: '',
        delivery_fee: '',
        min_order_amount: '',
        offers_delivery: false,
        agent_code: '',
        payout_phone: '',
        manager_first_name: '',
        manager_last_name: '',
        manager_email: '',
    });
    const [logoFile, setLogoFile] = useState(null);
    const [bannerFile, setBannerFile] = useState(null);
    const [previewLogo, setPreviewLogo] = useState(null);
    const [previewBanner, setPreviewBanner] = useState(null);
    // La description est réservée aux forfaits avec page personnalisée : le serveur refuse
    // toute requête qui la contient. On ne l'envoie donc que si elle a vraiment changé.
    const [initialDescription, setInitialDescription] = useState('');
    const [payoutsReady, setPayoutsReady] = useState(false);
    // Alertes de stock : modifiables seulement si le forfait inclut l'outil (forfait Pro).
    const [stockThreshold, setStockThreshold] = useState('');
    const [savedStockThreshold, setSavedStockThreshold] = useState('');
    const [stockAlertsIncluded, setStockAlertsIncluded] = useState(false);

    useEffect(() => {
        fetchStoreData();
    }, []);

    const fetchStoreData = async () => {
        try {
            const dashboardRes = await getStoreDashboard();
            if (dashboardRes.success) {
                const dashboardStore = dashboardRes.data.store || dashboardRes.data.store_info;
                const storeId = dashboardStore.id;
                const detailsRes = await getStoreDetails(storeId);
                if (detailsRes.success) {
                    const data = detailsRes.data;
                    setStore(data);
                    setFormData({
                        name: data.name || '',
                        description: data.description || '',
                        phone: data.phone || '',
                        email: data.email || '',
                        address: data.address || '',
                        zone: data.zone || '',
                        opening_time: data.opening_time || '',
                            closing_time: data.closing_time || '',
                            delivery_fee: data.delivery_fee || '',
                            min_order_amount: data.min_order_amount || '',
                            offers_delivery: !!data.offers_delivery,
                            agent_code: dashboardStore.agent_code || '',
                            payout_phone: dashboardStore.payout_phone || '',
                        manager_first_name: data.manager_details?.first_name || '',
                        manager_last_name: data.manager_details?.last_name || '',
                        manager_email: data.manager_details?.email || '',
                    });
                    setInitialDescription(data.description || '');
                    setPayoutsReady(!!dashboardStore.payouts_ready);
                    const threshold = normalizeThreshold(dashboardStore.stock_alert_threshold ?? 3);
                    setStockThreshold(threshold);
                    setSavedStockThreshold(threshold);
                    setStockAlertsIncluded(!!dashboardRes.data.subscription?.tools?.stock_alerts);
                    setPreviewLogo(data.logo);
                    setPreviewBanner(data.banner_image);
                }
            }
        } catch (error) {
            console.error("Error fetching store settings", error);
            notifyError(error, {
                action: 'Charger le profil du commerce',
                fallback: "Le profil du commerce n'a pas pu être chargé.",
            });
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        const next = type === 'checkbox' ? checked : value;
        setFormData(prev => ({ ...prev, [name]: next }));
    };

    const handleFileChange = (e, type) => {
        const file = e.target.files[0];
        if (file) {
            if (type === 'logo') {
                setLogoFile(file);
                setPreviewLogo(URL.createObjectURL(file));
            } else {
                setBannerFile(file);
                setPreviewBanner(URL.createObjectURL(file));
            }
        }
    };

    const handleThresholdChange = (e) => {
        setStockThreshold(normalizeThreshold(e.target.value));
    };

    // Champ vidé : on remet la dernière valeur enregistrée.
    const handleThresholdBlur = () => {
        if (normalizeThreshold(stockThreshold) === '') setStockThreshold(savedStockThreshold);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!store) {
            notifyWarning("Le profil du commerce n'est pas chargé", 'Rechargez la page, puis réessayez.');
            return;
        }
        let threshold = null;
        if (stockAlertsIncluded) {
            threshold = normalizeThreshold(stockThreshold);
            if (threshold === '') {
                notifyWarning(
                    'Indiquez le seuil des alertes de stock',
                    'Entrez un nombre de 0 à 1000 (0 = seulement à la rupture de stock), puis enregistrez.'
                );
                return;
            }
        }
        const data = new FormData();
        Object.keys(formData).forEach(key => {
            const value = formData[key];
            // Always send boolean flags (including false). For others, skip empty strings.
            if (key === 'description' && value === initialDescription) {
                return;
            }
            if (typeof value === 'boolean') {
                data.append(key, value ? 'true' : 'false');
            } else if (key === 'agent_code' || key === 'payout_phone') {
                // Toujours envoyés pour pouvoir aussi les effacer
                data.append(key, value || '');
            } else if (value !== null && value !== '') {
                data.append(key, value);
            }
        });
        if (logoFile) data.append('logo', logoFile);
        if (bannerFile) data.append('banner_image', bannerFile);
        if (threshold !== null) data.append('stock_alert_threshold', threshold);

        try {
            const res = await updateStore(store.id, data);
            if (res.success) {
                const thresholdChanged = threshold !== null && threshold !== savedStockThreshold;
                const thresholdText = threshold === '0'
                    ? 'seulement à la rupture de stock'
                    : `quand il reste ${threshold} unité(s) ou moins`;
                notifySuccess(
                    'Profil du commerce enregistré',
                    `Vos clients voient déjà les nouvelles informations.${thresholdChanged ? ` Alertes de stock : ${thresholdText}.` : ''}`
                );
                setStore(res.data);
                setInitialDescription(res.data?.description ?? formData.description);
                if (threshold !== null) {
                    setStockThreshold(threshold);
                    setSavedStockThreshold(threshold);
                }
            }
        } catch (error) {
            console.error("Error updating store", error);
            // Afficher la vraie raison renvoyée par le serveur (forfait, champ invalide…)
            const apiError = error.response?.data?.error;
            const message = apiError?.details
                ? Object.values(apiError.details).flat().join('\n')
                : apiError?.message || "Erreur lors de la mise à jour.";
            const details = apiError?.details && typeof apiError.details === 'object' && !Array.isArray(apiError.details)
                ? apiError.details
                : null;
            notifyError(
                details ? { error: { ...apiError, details: withFieldNames(details) } } : error,
                { action: 'Enregistrer le profil', fallback: message }
            );
        }
    };

    if (loading) return <StoreLayout title="Chargement..."><div>Chargement...</div></StoreLayout>;

    return (
        <StoreLayout title="Profil du Magasin">
            <div className="bg-white shadow rounded-lg p-6 max-w-4xl mx-auto">
                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Images Section */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Logo</label>
                            <div className="flex items-center space-x-4">
                                <div className="h-24 w-24 rounded-full overflow-hidden bg-gray-100 border">
                                    {previewLogo ? (
                                        <img src={previewLogo} alt="Logo" className="h-full w-full object-cover" />
                                    ) : (
                                        <span className="flex items-center justify-center h-full text-gray-400">No Logo</span>
                                    )}
                                </div>
                                <input type="file" onChange={(e) => handleFileChange(e, 'logo')} accept="image/*" />
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Bannière</label>
                            <div className="h-32 w-full rounded-lg overflow-hidden bg-gray-100 border">
                                {previewBanner ? (
                                    <img src={previewBanner} alt="Banner" className="h-full w-full object-cover" />
                                ) : (
                                    <span className="flex items-center justify-center h-full text-gray-400">No Banner</span>
                                )}
                            </div>
                            <input type="file" className="mt-2" onChange={(e) => handleFileChange(e, 'banner')} accept="image/*" />
                        </div>
                    </div>

                    {/* Manager Info */}
                    <div className="border-b pb-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Informations du commerçant</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Prénom</label>
                                <input 
                                    type="text" name="manager_first_name" value={formData.manager_first_name} onChange={handleChange}
                                    className="mt-1 block w-full border rounded-md shadow-sm p-2" 
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Nom</label>
                                <input 
                                    type="text" name="manager_last_name" value={formData.manager_last_name} onChange={handleChange}
                                    className="mt-1 block w-full border rounded-md shadow-sm p-2" 
                                />
                            </div>
                            <div className="md:col-span-2">
                                <label className="block text-sm font-medium text-gray-700">Email Personnel</label>
                                <input 
                                    type="email" name="manager_email" value={formData.manager_email} onChange={handleChange}
                                    className="mt-1 block w-full border rounded-md shadow-sm p-2" 
                                />
                            </div>
                        </div>
                    </div>

                    {/* Basic Info */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="md:col-span-2 rounded-md border border-indigo-100 bg-indigo-50 p-3 text-sm">
                            <span className="font-medium text-gray-700">Type de commerce : </span>
                            <span className="font-semibold text-indigo-800">{store?.category_name || 'Non renseigné'}</span>
                            <p className="mt-1 text-xs text-gray-600">Il fixe les catégories de produits proposées et leurs commissions. Pour le changer, contactez l'administrateur.</p>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Nom du magasin</label>
                            <input 
                                type="text" name="name" value={formData.name} onChange={handleChange}
                                className="mt-1 block w-full border rounded-md shadow-sm p-2" required 
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Téléphone</label>
                            <input 
                                type="text" name="phone" value={formData.phone} onChange={handleChange}
                                className="mt-1 block w-full border rounded-md shadow-sm p-2" required 
                            />
                        </div>
                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-gray-700">Description</label>
                            <textarea 
                                name="description" value={formData.description} onChange={handleChange}
                                className="mt-1 block w-full border rounded-md shadow-sm p-2" rows="3"
                            />
                        </div>
                    </div>

                    {/* Location & Contact */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Email</label>
                            <input 
                                type="email" name="email" value={formData.email} onChange={handleChange}
                                className="mt-1 block w-full border rounded-md shadow-sm p-2" 
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Zone</label>
                            <input 
                                type="text" name="zone" value={formData.zone} onChange={handleChange}
                                className="mt-1 block w-full border rounded-md shadow-sm p-2" 
                            />
                        </div>
                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-gray-700">Adresse complète</label>
                            <input 
                                type="text" name="address" value={formData.address} onChange={handleChange}
                                className="mt-1 block w-full border rounded-md shadow-sm p-2" 
                            />
                        </div>
                    </div>

                    {/* Business Settings */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Heure d'ouverture</label>
                            <input 
                                type="time" name="opening_time" value={formData.opening_time} onChange={handleChange}
                                className="mt-1 block w-full border rounded-md shadow-sm p-2" 
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Heure de fermeture</label>
                            <input 
                                type="time" name="closing_time" value={formData.closing_time} onChange={handleChange}
                                className="mt-1 block w-full border rounded-md shadow-sm p-2" 
                            />
                        </div>
                        <p className="md:col-span-2 -mt-3 text-xs text-gray-500">
                            Heure de Libreville. Même heure d'ouverture et de fermeture (ex. 00:00 et 00:00) : ouvert 24 h/24. Fermeture avant l'ouverture (ex. 18:00 et 02:00) : ouvert la nuit.
                        </p>
                        <div className="md:col-span-2 flex items-center space-x-3">
                            <input
                                id="offers_delivery"
                                name="offers_delivery"
                                type="checkbox"
                                checked={!!formData.offers_delivery}
                                onChange={handleChange}
                                className="h-4 w-4 text-indigo-600 border-gray-300 rounded"
                            />
                            <label htmlFor="offers_delivery" className="text-sm text-gray-700">Le magasin gère la livraison avec ses propres livreurs</label>
                        </div>
                        <p className="md:col-span-2 -mt-3 text-xs text-gray-500">
                            Si coché, Gaboshop ne paie pas de livreur : vous recevez la part livraison avec le versement du commerce, en un seul paiement. Par défaut : décoché (livreurs indépendants Gaboshop).
                        </p>
                        <div className="md:col-span-2 rounded-md border border-gray-200 p-4 space-y-3">
                            <div>
                                <h3 className="text-sm font-semibold text-gray-900">Recevoir vos ventes payées en ligne</h3>
                                <p className="mt-1 text-xs text-gray-500">
                                    Quand vous confirmez une commande payée en ligne, Gaboshop vous verse votre part (produits moins commission) sur le code agent ou le numéro ci-dessous.
                                </p>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Numéro Mobile Money</label>
                                    <input
                                        type="tel" name="payout_phone" value={formData.payout_phone} onChange={handleChange}
                                        autoComplete="off" maxLength={20} inputMode="tel"
                                        className="mt-1 block w-full border rounded-md shadow-sm p-2"
                                        placeholder="Ex. 077 12 34 56"
                                    />
                                    <p className="mt-1 text-xs text-gray-500">{payoutOperatorText(formData.payout_phone)}</p>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Code agent Mobile Money (option)</label>
                                    <input
                                        type="text" name="agent_code" value={formData.agent_code} onChange={handleChange}
                                        autoComplete="off" maxLength={100}
                                        className="mt-1 block w-full border rounded-md shadow-sm p-2"
                                        placeholder="Si vous avez un code agent"
                                    />
                                </div>
                            </div>
                            <p className={`text-xs ${payoutsReady ? 'text-green-700' : 'text-amber-700'}`}>
                                {payoutsReady
                                    ? 'Versements activés : Gaboshop a enregistré votre compte chez SingPay.'
                                    : "Versements en attente : Gaboshop doit d'abord enregistrer votre numéro ou code agent chez SingPay. D'ici là, vos ventes vous sont versées à la main."}
                            </p>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Frais de livraison (FCFA)</label>
                            <input 
                                type="number" name="delivery_fee" value={formData.delivery_fee} onChange={handleChange}
                                className="mt-1 block w-full border rounded-md shadow-sm p-2" 
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Montant min. commande (FCFA)</label>
                            <input 
                                type="number" name="min_order_amount" value={formData.min_order_amount} onChange={handleChange}
                                className="mt-1 block w-full border rounded-md shadow-sm p-2" 
                            />
                        </div>
                    </div>

                    {/* Alertes de stock (outil du forfait Pro) */}
                    <div className={`rounded-md border border-gray-200 p-4 space-y-3 ${stockAlertsIncluded ? '' : 'bg-gray-50'}`}>
                        <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-sm font-semibold text-gray-900">Alertes de stock</h3>
                            {!stockAlertsIncluded && (
                                <span className="inline-block rounded bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">Forfait Pro</span>
                            )}
                        </div>
                        <div className="flex flex-wrap items-center gap-2 text-sm text-gray-700">
                            <label htmlFor="stock_alert_threshold">Prévenez-moi quand il reste</label>
                            <input
                                id="stock_alert_threshold" name="stock_alert_threshold"
                                type="number" min={0} max={STOCK_ALERT_MAX} step={1} inputMode="numeric"
                                value={stockThreshold} onChange={handleThresholdChange} onBlur={handleThresholdBlur}
                                onKeyDown={blockNonInteger} disabled={!stockAlertsIncluded}
                                aria-describedby="stock_alert_help"
                                className="w-24 border rounded-md shadow-sm p-2 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400"
                            />
                            <span>unité(s) ou moins</span>
                        </div>
                        <p id="stock_alert_help" className="text-xs text-gray-500">
                            0 = seulement à la rupture de stock. Vous recevez une notification sur votre téléphone et dans l'application.
                        </p>
                        {!stockAlertsIncluded && (
                            <div className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-md border border-amber-200 bg-amber-50 p-3">
                                <div className="min-w-0 flex-1">
                                    <p className="break-words text-sm font-medium text-amber-900">Alertes de stock faible : forfait Pro</p>
                                    <p className="mt-0.5 break-words text-xs text-amber-800">Soyez prévenu avant qu'un produit soit épuisé.</p>
                                </div>
                                <Link
                                    to="/store/subscription"
                                    className="inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
                                >
                                    Passer au forfait Pro
                                </Link>
                            </div>
                        )}
                    </div>

                    <div className="flex justify-end">
                        <button 
                            type="submit" 
                            className="bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                        >
                            Enregistrer les modifications
                        </button>
                    </div>
                </form>
            </div>
        </StoreLayout>
    );
};

export default StoreProfile;
