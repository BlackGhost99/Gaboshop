import React from 'react';
import { Link, useLocation } from 'react-router-dom';

/** Demande au visiteur de se connecter ou de s'inscrire avant d'ajouter au panier. */
const LoginRequiredModal = ({ productName, onClose }) => {
  const location = useLocation();
  const next = encodeURIComponent(`${location.pathname}${location.search}`);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-[80] sm:px-4" onClick={onClose}>
      <div
        className="bg-white w-full sm:max-w-sm rounded-t-2xl sm:rounded-2xl shadow-2xl p-6"
        style={{ paddingBottom: 'max(1.5rem, env(safe-area-inset-bottom))' }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Connexion requise"
      >
        <h3 className="text-lg font-bold text-gray-900">Connectez-vous pour acheter</h3>
        <p className="text-sm text-gray-600 mt-2">
          {productName ? <>Pour ajouter <strong>{productName}</strong> au panier, </> : 'Pour ajouter un produit au panier, '}
          connectez-vous ou créez un compte gratuit. Le produit sera ajouté dès votre retour.
        </p>
        <div className="mt-5 flex flex-col gap-3">
          <Link
            to={`/login?next=${next}`}
            className="w-full text-center bg-slate-900 hover:bg-slate-800 text-white font-medium px-4 py-3 rounded-lg"
          >
            Se connecter
          </Link>
          <Link
            to={`/register?next=${next}`}
            className="w-full text-center border border-slate-300 text-slate-900 font-medium px-4 py-3 rounded-lg hover:bg-slate-50"
          >
            Créer un compte
          </Link>
          <button onClick={onClose} className="text-sm text-gray-500 py-1">
            Plus tard
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoginRequiredModal;
