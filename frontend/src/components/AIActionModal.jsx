import React from 'react';

const AIActionModal = ({ isOpen, onClose, actionData, onConfirm, onCancel, isLoading }) => {
  if (!isOpen || !actionData) return null;

  const { summary, items, totals, store, requires_confirmation } = actionData;

  const handleConfirm = () => {
    if (onConfirm) {
      onConfirm(actionData);
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden animate-slide-up">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-white font-bold text-lg">Confirmer l'action</h3>
            <button
              onClick={handleCancel}
              className="text-white/80 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Summary */}
          <div>
            <p className="text-gray-700 font-medium">{summary}</p>
            {store && (
              <p className="text-sm text-gray-500 mt-1">Magasin: {store.name}</p>
            )}
          </div>

          {/* Items */}
          {items && items.length > 0 && (
            <div className="border-t pt-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Détails:</h4>
              <div className="space-y-2">
                {items.map((item, idx) => (
                  <div key={idx} className="flex justify-between text-sm">
                    <span className="text-gray-600">
                      {item.quantity}x {item.product?.name || 'Produit'}
                    </span>
                    <span className="text-gray-900 font-medium">
                      {item.subtotal?.toLocaleString('fr-FR')} FCFA
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Totals */}
          {totals && (
            <div className="border-t pt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Sous-total:</span>
                <span className="text-gray-900">{totals.items_total?.toLocaleString('fr-FR')} FCFA</span>
              </div>
              {totals.delivery_fee > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Livraison:</span>
                  <span className="text-gray-900">{totals.delivery_fee?.toLocaleString('fr-FR')} FCFA</span>
                </div>
              )}
              {totals.service_fee > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Frais de service:</span>
                  <span className="text-gray-900">{totals.service_fee?.toLocaleString('fr-FR')} FCFA</span>
                </div>
              )}
              <div className="flex justify-between text-lg font-bold pt-2 border-t">
                <span>Total:</span>
                <span className="text-indigo-600">{totals.total?.toLocaleString('fr-FR')} FCFA</span>
              </div>
            </div>
          )}

          {/* Warning */}
          {requires_confirmation && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <p className="text-sm text-yellow-800">
                ⚠️ Veuillez vérifier les détails avant de confirmer.
              </p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="bg-gray-50 px-6 py-4 flex gap-3">
          <button
            onClick={handleCancel}
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors disabled:opacity-50"
          >
            Annuler
          </button>
          <button
            onClick={handleConfirm}
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                <span>Confirmation...</span>
              </>
            ) : (
              'Confirmer'
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AIActionModal;

