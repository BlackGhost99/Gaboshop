import React from 'react';

/**
 * Composant Modal réutilisable
 */
const Modal = ({ 
	isOpen, 
	onClose, 
	title, 
	children, 
	showCloseButton = true,
	size = 'md', // 'sm', 'md', 'lg', 'xl'
	onConfirm,
	confirmText = 'OK',
	cancelText = 'Annuler',
	showCancel = false,
	confirmButtonClass = 'bg-indigo-600 hover:bg-indigo-700',
	loading = false
}) => {
	if (!isOpen) return null;

	const sizeClasses = {
		sm: 'max-w-sm',
		md: 'max-w-md',
		lg: 'max-w-lg',
		xl: 'max-w-2xl',
	};

	return (
		<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
			<div className={`bg-white rounded-lg shadow-xl w-full ${sizeClasses[size]} max-h-[90vh] overflow-y-auto`}>
				{/* Header */}
				{(title || showCloseButton) && (
					<div className="flex justify-between items-center p-6 border-b border-gray-200">
						{title && (
							<h3 className="text-xl font-bold text-gray-900">{title}</h3>
						)}
						{showCloseButton && (
							<button
								onClick={onClose}
								className="text-gray-400 hover:text-gray-600 transition-colors"
								disabled={loading}
							>
								<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
								</svg>
							</button>
						)}
					</div>
				)}

				{/* Content */}
				<div className="p-6">
					{children}
				</div>

				{/* Footer */}
				{(onConfirm || showCancel) && (
					<div className="flex justify-end gap-3 p-6 border-t border-gray-200">
						{showCancel && (
							<button
								onClick={onClose}
								className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
								disabled={loading}
							>
								{cancelText}
							</button>
						)}
						{onConfirm && (
							<button
								onClick={onConfirm}
								disabled={loading}
								className={`px-4 py-2 text-white rounded-md transition-colors font-medium ${confirmButtonClass} ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
							>
								{loading ? 'Chargement...' : confirmText}
							</button>
						)}
					</div>
				)}
			</div>
		</div>
	);
};

export default Modal;

