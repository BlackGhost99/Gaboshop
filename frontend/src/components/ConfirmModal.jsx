import React from 'react';
import Modal from './Modal';

/**
 * Composant Modal de confirmation
 * Remplace window.confirm()
 */
const ConfirmModal = ({
  isOpen,
  onClose,
  title = 'Confirmation',
  message,
  confirmText = 'Confirmer',
  cancelText = 'Annuler',
  onConfirm,
  variant = 'info',
  autoClose = true, // Si false, le modal ne se ferme pas automatiquement après onConfirm
  loading = false, // État de chargement pour désactiver le bouton
}) => {
  const [isProcessing, setIsProcessing] = React.useState(false);
  
  const handleConfirm = async () => {
    if (isProcessing || loading) return;
    
    setIsProcessing(true);
    try {
      if (onConfirm) {
        const result = await onConfirm();
        // Ne fermer que si autoClose est true ou si onConfirm retourne explicitement true
        if (autoClose || result === true) {
          onClose();
        }
      } else {
        onClose();
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const variantClasses = {
    danger: 'bg-red-600 hover:bg-red-700 text-white',
    warning: 'bg-yellow-600 hover:bg-yellow-700 text-white',
    info: 'bg-blue-600 hover:bg-blue-700 text-white',
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="sm"
      closeOnOverlayClick={false}
    >
      <div className="space-y-4">
        <p className="text-gray-700">{message}</p>

        <div className="flex justify-end gap-3 pt-4">
          <button
            onClick={onClose}
            disabled={isProcessing || loading}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {cancelText}
          </button>
          <button
            onClick={handleConfirm}
            disabled={isProcessing || loading}
            className={`px-4 py-2 rounded-lg font-semibold transition-colors ${variantClasses[variant]} disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default ConfirmModal;


