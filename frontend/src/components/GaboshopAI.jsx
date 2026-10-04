import React, { useState, useEffect, useRef } from 'react';
import { useAIContext } from '../context/AIContext';
import AIActionModal from './AIActionModal';
import aiService from '../services/aiService';

const GaboshopAI = () => {
    const { 
        messages, 
        isLoading, 
        lastError, 
        sendMessage, 
        clearMessages,
        clearError 
    } = useAIContext();
    
    const [isOpen, setIsOpen] = useState(false);
    const [inputValue, setInputValue] = useState('');
    const [actionModal, setActionModal] = useState(null);
    const [confirmingAction, setConfirmingAction] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isOpen]);

    // Afficher automatiquement une explication d'erreur si présente
    useEffect(() => {
        if (lastError && isOpen && messages.length === 0) {
            const errorMessage = `Je remarque qu'une erreur s'est produite (code ${lastError.status}). ` +
                `Souhaitez-vous que je vous explique ce qui s'est passé et comment résoudre le problème ?`;
            sendMessage("Explique-moi cette erreur");
        }
    }, [lastError, isOpen]);

    const handleSend = async () => {
        if (!inputValue.trim() || isLoading) return;
        
        const message = inputValue.trim();
        setInputValue('');
        
        // Détecter les intentions d'action
        const lowerMessage = message.toLowerCase();
        const isOrderIntent = lowerMessage.includes('commander') || 
                             lowerMessage.includes('acheter') || 
                             lowerMessage.includes('commande') ||
                             lowerMessage.includes('ajouter au panier');
        
        if (isOrderIntent) {
            // Préparer la commande
            try {
                const response = await aiService.prepareOrder(message);
                if (response.success && response.data.requires_confirmation) {
                    setActionModal({
                        type: 'order',
                        data: response.data,
                    });
                } else {
                    // Si pas de confirmation requise, envoyer le message normal
                    await sendMessage(message);
                }
            } catch (error) {
                // Gérer les différents types d'erreurs
                const status = error.response?.status;
                const errorData = error.response?.data;
                
                if (status === 503) {
                    // Service non disponible (mode local)
                    const errorMsg = errorData?.error?.message || 
                        "La préparation de commande par IA nécessite un service d'IA configuré. Cette fonctionnalité n'est pas disponible en mode local.\n\nVous pouvez créer des commandes manuellement depuis la page des produits.";
                    await sendMessage(`Je ne peux pas préparer de commande automatiquement en mode local. ${errorMsg}`);
                } else if (status === 500) {
                    // Erreur serveur
                    const errorMsg = errorData?.error?.message || 
                        "Une erreur s'est produite lors de la préparation de votre commande. Veuillez réessayer ou créer la commande manuellement.";
                    await sendMessage(`Désolé, j'ai rencontré une erreur : ${errorMsg}\n\nSouhaitez-vous que je vous aide autrement ?`);
                } else if (status === 403) {
                    // Permission refusée
                    const errorMsg = errorData?.error?.message || 
                        "Vous n'avez pas les permissions nécessaires pour cette action.";
                    await sendMessage(`Je ne peux pas préparer cette commande : ${errorMsg}`);
                } else {
                    // Autre erreur, envoyer le message normal pour avoir une réponse de l'IA
                    console.error('Erreur prepare_order:', error);
                    await sendMessage(message);
                }
            }
        } else {
            // Message normal
            await sendMessage(message);
        }
    };

    const handleConfirmAction = async () => {
        if (!actionModal) return;
        
        setConfirmingAction(true);
        try {
            const response = await aiService.confirmAction(
                actionModal.type,
                actionModal.data,
                {
                    delivery_address: prompt('Adresse de livraison:') || '',
                    delivery_zone: prompt('Zone de livraison:') || '',
                }
            );
            
            if (response.success) {
                // Ajouter un message de succès
                const successMsg = {
                    id: Date.now(),
                    type: 'bot',
                    text: `✅ ${response.data.message || 'Action confirmée avec succès!'}`,
                    timestamp: new Date().toISOString(),
                };
                // Note: On devrait utiliser le contexte pour ajouter le message
                // Pour l'instant, on ferme juste le modal
                setActionModal(null);
            }
        } catch (error) {
            alert('Erreur lors de la confirmation: ' + (error.response?.data?.error?.message || error.message));
        } finally {
            setConfirmingAction(false);
        }
    };

    const handleCancelAction = () => {
        setActionModal(null);
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    // Suggestions contextuelles selon la page
    const getSuggestions = () => {
        const suggestions = [
            "Comment puis-je vous aider ?",
            "Explique-moi cette erreur",
            "Quelles sont mes statistiques ?"
        ];
        return suggestions;
    };

    return (
        <div className="fixed bottom-6 right-6 z-50 font-sans">
            {/* Chat Window */}
            {isOpen && (
                <div className="bg-white/90 backdrop-blur-md border border-white/20 shadow-2xl rounded-2xl w-80 sm:w-96 flex flex-col mb-4 overflow-hidden animate-slide-up ring-1 ring-black/5">
                    {/* Header */}
                    <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-4 flex justify-between items-center">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm">
                                <span className="text-xl">🤖</span>
                            </div>
                            <div>
                                <h3 className="text-white font-bold text-sm">Gaboshop AI</h3>
                                <p className="text-indigo-100 text-xs flex items-center gap-1">
                                    <span className={`w-2 h-2 rounded-full animate-pulse ${isLoading ? 'bg-yellow-400' : 'bg-green-400'}`}></span>
                                    {isLoading ? 'En cours...' : 'En ligne'}
                                </p>
                            </div>
                        </div>
                        <div className="flex gap-2">
                            {lastError && (
                                <button
                                    onClick={clearError}
                                    className="text-white/80 hover:text-white text-xs px-2 py-1 bg-white/20 rounded"
                                    title="Effacer l'erreur"
                                >
                                    ✕
                                </button>
                            )}
                            <button onClick={() => setIsOpen(false)} className="text-white/80 hover:text-white">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                    </div>

                    {/* Alertes d'erreur */}
                    {lastError && (
                        <div className="bg-red-50 border-l-4 border-red-500 p-3 mx-4 mt-2 rounded">
                            <div className="flex items-center">
                                <span className="text-red-500 text-sm font-semibold">
                                    Erreur {lastError.status}
                                </span>
                            </div>
                            <p className="text-red-700 text-xs mt-1">
                                {lastError.endpoint}
                            </p>
                        </div>
                    )}

                    {/* Messages */}
                    <div className="h-80 overflow-y-auto p-4 space-y-3 bg-slate-50/50">
                        {messages.length === 0 && (
                            <div className="text-center text-gray-500 text-sm py-4">
                                <p className="mb-2">Bonjour ! Je suis l'IA de Gaboshop.</p>
                                <p>Comment puis-je vous aider aujourd'hui ?</p>
                            </div>
                        )}
                        
                        {messages.map((msg) => (
                            <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm shadow-sm ${
                                    msg.type === 'user'
                                        ? 'bg-indigo-600 text-white rounded-br-none'
                                        : msg.isError
                                        ? 'bg-red-50 text-red-800 border border-red-200 rounded-bl-none'
                                        : 'bg-white text-gray-800 border border-gray-100 rounded-bl-none'
                                }`}>
                                    {msg.text}
                                </div>
                            </div>
                        ))}
                        
                        {isLoading && (
                            <div className="flex justify-start">
                                <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-none px-4 py-2 flex gap-1 shadow-sm">
                                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Suggestions rapides */}
                    {messages.length === 0 && !isLoading && (
                        <div className="px-4 pb-2">
                            <div className="flex flex-wrap gap-2">
                                {getSuggestions().slice(0, 2).map((suggestion, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => sendMessage(suggestion)}
                                        className="text-xs px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full hover:bg-indigo-100 transition-colors"
                                    >
                                        {suggestion}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Input */}
                    <div className="p-3 bg-white border-t border-gray-100">
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                onKeyPress={handleKeyPress}
                                placeholder="Posez une question..."
                                disabled={isLoading}
                                className="flex-1 bg-gray-100 border-0 rounded-full px-4 py-2 text-sm focus:ring-2 focus:ring-indigo-500 transition-all disabled:opacity-50"
                            />
                            <button
                                onClick={handleSend}
                                disabled={isLoading || !inputValue.trim()}
                                className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-full p-2 transition-colors flex-shrink-0"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Floating Button */}
            {!isOpen && (
                <button
                    onClick={() => setIsOpen(true)}
                    className="group flex items-center justify-center w-14 h-14 bg-gradient-to-br from-indigo-600 to-purple-600 text-white rounded-full shadow-lg hover:shadow-indigo-500/50 hover:scale-110 transition-all duration-300 relative"
                >
                    <span className="text-2xl animate-[wiggle_1s_ease-in-out_infinite]">🤖</span>
                    {lastError && (
                        <span className="absolute -top-1 -right-1 flex h-4 w-4">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-4 w-4 bg-red-500 text-[10px] items-center justify-center font-bold">!</span>
                        </span>
                    )}
                    <div className="absolute right-full mr-4 bg-white px-3 py-1 rounded-lg shadow-md text-gray-800 text-sm font-medium whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                        {lastError ? 'Erreur détectée' : 'Besoin d\'aide ?'}
                    </div>
                </button>
            )}

            <style>{`
                @keyframes slide-up { 
                    from { opacity: 0; transform: translateY(20px); } 
                    to { opacity: 1; transform: translateY(0); } 
                }
                @keyframes wiggle { 
                    0%, 100% { transform: rotate(-3deg); } 
                    50% { transform: rotate(3deg); } 
                }
            `}</style>

            {/* Action Modal */}
            {actionModal && (
                <AIActionModal
                    isOpen={!!actionModal}
                    onClose={handleCancelAction}
                    actionData={actionModal.data}
                    onConfirm={handleConfirmAction}
                    onCancel={handleCancelAction}
                    isLoading={confirmingAction}
                />
            )}
        </div>
    );
};

export default GaboshopAI;
