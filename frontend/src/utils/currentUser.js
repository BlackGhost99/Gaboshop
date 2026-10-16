import { useEffect, useState } from 'react';
import api from '../services/api';
import authStorage from './authStorage';

// Rôle de la personne connectée (client, store_manager, delivery_agent, admin).
// Gardé avec le jeton qui l'a fourni : un autre compte sur le même appareil ne reprend jamais le rôle du précédent.
const ROLE_KEY = 'user_role';

const tokenTag = () => (authStorage.getItem('token') || '').slice(-16);

export const rememberRole = (role) => {
  if (!role) return;
  try {
    authStorage.setItem(ROLE_KEY, `${tokenTag()}|${role}`);
  } catch {
    // stockage indisponible
  }
};

export const readRole = () => {
  try {
    const [tag, role] = (authStorage.getItem(ROLE_KEY) || '').split('|');
    return tag && tag === tokenTag() ? role || null : null;
  } catch {
    return null;
  }
};

export const forgetRole = () => {
  try {
    authStorage.removeItem(ROLE_KEY);
  } catch {
    // stockage indisponible
  }
};

let pending = null;
export const loadRole = async () => {
  if (!authStorage.getItem('token')) return null;
  const known = readRole();
  if (known) return known;
  if (!pending) {
    pending = api.get('/auth/profile/')
      .then((res) => {
        const role = res.data?.data?.user_type || null;
        rememberRole(role);
        return role;
      })
      .catch(() => null)
      .finally(() => { pending = null; });
  }
  return pending;
};

// Rôle de la personne connectée, ou null (visiteur, ou rôle en cours de chargement).
export function useRole() {
  const [role, setRole] = useState(() => readRole());
  useEffect(() => {
    let active = true;
    loadRole().then((value) => { if (active) setRole(value); });
    return () => { active = false; };
  }, []);
  return role;
}

export const ROLE_HOME = {
  client: '/client/dashboard',
  store_manager: '/store/dashboard',
  delivery_agent: '/delivery/dashboard',
  admin: '/admin/dashboard',
};
