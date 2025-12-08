import React, { useState, useEffect } from 'react';
import StoreLayout from '../../components/StoreLayout';
import { getStoreDashboard } from '../../services/dashboardService';
import { getStoreDetails, updateStore } from '../../services/storeService';

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
        manager_first_name: '',
        manager_last_name: '',
        manager_email: '',
    });
    const [logoFile, setLogoFile] = useState(null);
    const [bannerFile, setBannerFile] = useState(null);
    const [previewLogo, setPreviewLogo] = useState(null);
    const [previewBanner, setPreviewBanner] = useState(null);

    useEffect(() => {
        fetchStoreData();
    }, []);

    const fetchStoreData = async () => {
        try {
            const dashboardRes = await getStoreDashboard();
            if (dashboardRes.success) {
                const storeId = (dashboardRes.data.store || dashboardRes.data.store_info).id;
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
                        manager_first_name: data.manager_details?.first_name || '',
                        manager_last_name: data.manager_details?.last_name || '',
                        manager_email: data.manager_details?.email || '',
                    });
                    setPreviewLogo(data.logo);
                    setPreviewBanner(data.banner_image);
                }
            }
        } catch (error) {
            console.error("Error fetching store settings", error);
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
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

    const handleSubmit = async (e) => {
        e.preventDefault();
        const data = new FormData();
        Object.keys(formData).forEach(key => {
            // Only append if value is not null/undefined/empty string
            // For time/decimal fields, empty string is invalid
            if (formData[key] !== null && formData[key] !== '') {
                data.append(key, formData[key]);
            }
        });
        if (logoFile) data.append('logo', logoFile);
        if (bannerFile) data.append('banner_image', bannerFile);

        try {
            const res = await updateStore(store.id, data);
            if (res.success) {
                alert("Profil mis à jour avec succès !");
                setStore(res.data);
            }
        } catch (error) {
            console.error("Error updating store", error);
            const message = error.error?.details 
                ? Object.values(error.error.details).flat().join('\n')
                : "Erreur lors de la mise à jour.";
            alert(message);
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
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Informations du Gérant</h3>
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
