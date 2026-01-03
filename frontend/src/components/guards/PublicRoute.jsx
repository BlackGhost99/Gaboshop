import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import LoadingSpinner from '../LoadingSpinner';

/**
 * Routes accessibles UNIQUEMENT aux clients non-stores
 * Bloque automatiquement les store_managers et les redirige vers leur dashboard
 */
export default function PublicRoute({ children }) {
	const navigate = useNavigate();
	const [isAllowed, setIsAllowed] = useState(null);

	useEffect(() => {
		const checkUserType = async () => {
			const token = sessionStorage.getItem('token');
			
			// Si non authentifié, autoriser l'accès (site public)
			if (!token) {
				setIsAllowed(true);
				return;
			}

			try {
				const response = await api.get('/auth/profile/');
				if (response.data.success) {
					const userType = response.data.data.user_type;
					
					// BLOQUER les store_managers du site public
					if (userType === 'store_manager') {
						navigate('/store/dashboard');
					} else {
						// Autoriser les clients et autres rôles
						setIsAllowed(true);
					}
				} else {
					// En cas d'erreur, autoriser quand même (site public)
					setIsAllowed(true);
				}
			} catch (err) {
				// En cas d'erreur (ex: token expiré), autoriser quand même (site public)
				console.error('Erreur de vérification du type d\'utilisateur:', err);
				setIsAllowed(true);
			}
		};

		checkUserType();
	}, [navigate]);

	if (isAllowed === null) {
		return <LoadingSpinner />;
	}

	return isAllowed ? children : null;
}

