import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import LoadingSpinner from '../LoadingSpinner';

/**
 * Composant réutilisable pour routes authentifiées avec contrôle de rôle
 * @param {Object} props
 * @param {React.ReactNode} props.children - Composants enfants à afficher si autorisé
 * @param {string[]} props.allowedRoles - Liste des rôles autorisés (ex: ['client', 'store_manager'])
 */
export default function PrivateRoute({ children, allowedRoles = [] }) {
	const navigate = useNavigate();
	const [isAuthorized, setIsAuthorized] = useState(null);

	useEffect(() => {
		const checkAuth = async () => {
			const token = sessionStorage.getItem('token');
			if (!token) {
				navigate('/login');
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
	}, [navigate, allowedRoles]);

	if (isAuthorized === null) {
		return <LoadingSpinner />;
	}

	return isAuthorized ? children : null;
}

