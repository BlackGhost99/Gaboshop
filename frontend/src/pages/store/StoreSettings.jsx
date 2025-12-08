import React from 'react';
import { Link } from 'react-router-dom';
import StoreLayout from '../../components/StoreLayout';

const StoreSettings = () => {
    return (
        <StoreLayout title="Paramètres">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Profile Card */}
                <Link to="/store/settings/profile" className="block">
                    <div className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow cursor-pointer h-full">
                        <div className="flex items-center space-x-4 mb-4">
                            <div className="bg-indigo-100 p-3 rounded-full">
                                <svg className="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                </svg>
                            </div>
                            <h3 className="text-lg font-medium text-gray-900">Profil du Magasin</h3>
                        </div>
                        <p className="text-gray-500 text-sm">
                            Gérez les informations de votre magasin, logo, bannière et coordonnées.
                        </p>
                    </div>
                </Link>

                {/* Other settings placeholders */}
                <div className="bg-white shadow rounded-lg p-6 opacity-50">
                    <div className="flex items-center space-x-4 mb-4">
                        <div className="bg-gray-100 p-3 rounded-full">
                            <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                        </div>
                        <h3 className="text-lg font-medium text-gray-900">Sécurité</h3>
                    </div>
                    <p className="text-gray-500 text-sm">
                        Changez votre mot de passe et gérez les accès (Bientôt disponible).
                    </p>
                </div>

                <div className="bg-white shadow rounded-lg p-6 opacity-50">
                    <div className="flex items-center space-x-4 mb-4">
                        <div className="bg-gray-100 p-3 rounded-full">
                            <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                            </svg>
                        </div>
                        <h3 className="text-lg font-medium text-gray-900">Paiements</h3>
                    </div>
                    <p className="text-gray-500 text-sm">
                        Configurez vos méthodes de retrait et consultez l'historique (Bientôt disponible).
                    </p>
                </div>
            </div>
        </StoreLayout>
    );
};

export default StoreSettings;


