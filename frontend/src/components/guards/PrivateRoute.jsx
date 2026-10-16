import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import LoadingSpinner from '../LoadingSpinner';
import authStorage from '../../utils/authStorage';
import PhoneVerifyBanner from '../PhoneVerifyBanner';

/**
 * Composant réutilisable pour routes authentifiées avec contrôle de rôle
 * @param {Object} props
 * @param {React.ReactNode} props.children - Composants enfants à afficher si autorisé
 * @param {string[]} props.allowedRoles - Liste des rôles autorisés (ex: ['client', 'store_manager'])
 */
const ANY_ROLE = [];

export default function PrivateRoute({ children, allowedRoles = ANY_ROLE }) {
	const navigate = useNavigate();
	const location = useLocation();
	const [isAuthorized, setIsAuthorized] = useState(null);

	useEffect(() => {
		const checkAuth = async () => {
			const token = authStorage.getItem('token');
			if (!token) {
				// Retour là où la personne allait (notification touchée, panier…) une fois connectée.
				const wanted = `${location.pathname}${location.search}${location.hash}`;
				navigate(wanted && wanted !== '/' ? `/login?next=${encodeURIComponent(wanted)}` : '/login');
				return;
			}

			try {
				const response = await api.get('/auth/profile/');
				if (response.data.success) {
					const userType = response.data.data.user_type;
					
					// Si aucun rôle spécifique requis, autoriser tous les utilisateurs authentifiés
					if (allowedRoles.length === 0 || allowedRoles.includes(userType)) {
						setIsAuthorized(true);
					} else {
						// Rediriger vers le dashboard approprié
						navigate('/dashboard');
					}
				} else {
					navigate('/login');
				}
			} catch (err) {
				console.error('Erreur de vérification d\'authentification:', err);
				navigate('/login');
			}
		};

		checkAuth();
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [navigate, allowedRoles]);

	if (isAuthorized === null) {
		return <LoadingSpinner />;
	}

	return isAuthorized ? <><PhoneVerifyBanner />{children}</> : null;
}

