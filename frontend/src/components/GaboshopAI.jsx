import React, { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

const GaboshopAI = ({ userName, contextData }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([
        { id: 1, type: 'bot', text: 'Bonjour ! Je suis l\'IA de Gaboshop. Comment puis-je vous aider aujourd\'hui ?' }
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const messagesEndRef = useRef(null);
    const location = useLocation();

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isOpen]);

    const handleSend = async () => {
        if (!inputValue.trim()) return;

        const userMsg = { id: Date.now(), type: 'user', text: inputValue };
        setMessages(prev => [...prev, userMsg]);
        setInputValue('');
        setIsTyping(true);

        // Simulate AI processing
        setTimeout(() => {
            const response = generateResponse(userMsg.text, location.pathname, contextData);
            setMessages(prev => [...prev, { id: Date.now() + 1, type: 'bot', text: response }]);
            setIsTyping(false);
        }, 1500);
    };

    const generateResponse = (text, path, data) => {
        const lower = text.toLowerCase();

        // Store Dashboard Context
        if (path.includes('/store')) {
            if (lower.includes('vente') || lower.includes('chiffre')) {
                return `Vos ventes du jour s'élèvent à ${data?.daily_revenue || '0 FCFA'}. C'est une belle progression ! 📈`;
            }
            if (lower.includes('commande')) {
                return `Vous avez ${data?.daily_orders_count || 0} nouvelles commandes aujourd'hui. N'oubliez pas de les traiter rapidement ! 🚀`;
            }
            if (lower.includes('grossiste') || lower.includes('stock') || lower.includes('appro')) {
                return "Pour vous réapprovisionner, rendez-vous dans l'onglet 'Approvisionnement' de votre tableau de bord. Vous y trouverez nos partenaires industriels.";
            }
        }

        // Client Dashboard Context
        if (path.includes('/client')) {
            if (lower.includes('commande')) {
                return "Vous pouvez suivre l'état de vos commandes dans la section 'Mes Commandes'. Un livreur vous sera attribué dès confirmation.";
            }
            if (lower.includes('livraison')) {
                return "La livraison standard est de 2000 FCFA. Pour une livraison Express, comptez 3500 FCFA.";
            }
        }

        // General
        if (lower.includes('bonjour') || lower.includes('salut')) {
            return `Salut ${userName || ''} ! Ravi de vous voir. Que puis-je faire pour vous ?`;
        }
        if (lower.includes('aide')) {
            return "Je peux vous donner des infos sur vos commandes, vos ventes, ou vous guider sur la plateforme.";
        }

        return "Je ne suis pas sûr de comprendre, mais je suis là pour apprendre ! Essayez de me demander vos statistiques ou le statut de vos commandes.";
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
                                    <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                                    En ligne
                                </p>
                            </div>
                        </div>
                        <button onClick={() => setIsOpen(false)} className="text-white/80 hover:text-white">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {/* Messages */}
                    <div className="h-80 overflow-y-auto p-4 space-y-3 bg-slate-50/50">
                        {messages.map((msg) => (
                            <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm shadow-sm ${msg.type === 'user'
                                        ? 'bg-indigo-600 text-white rounded-br-none'
                                        : 'bg-white text-gray-800 border border-gray-100 rounded-bl-none'
                                    }`}>
                                    {msg.text}
                                </div>
                            </div>
                        ))}
                        {isTyping && (
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

                    {/* Input */}
                    <div className="p-3 bg-white border-t border-gray-100">
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                                placeholder="Posez une question..."
                                className="flex-1 bg-gray-100 border-0 rounded-full px-4 py-2 text-sm focus:ring-2 focus:ring-indigo-500 transition-all"
                            />
                            <button
                                onClick={handleSend}
                                className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-full p-2 transition-colors flex-shrink-0"
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
                    <span className="absolute -top-1 -right-1 flex h-4 w-4">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-4 w-4 bg-red-500 text-[10px] items-center justify-center font-bold">1</span>
                    </span>
                    <div className="absolute right-full mr-4 bg-white px-3 py-1 rounded-lg shadow-md text-gray-800 text-sm font-medium whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                        Besoin d'aide ?
                    </div>
                </button>
            )}

            <style>{`
        @keyframes slide-up { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes wiggle { 0%, 100% { transform: rotate(-3deg); } 50% { transform: rotate(3deg); } }
      `}</style>
        </div>
    );
};

export default GaboshopAI;
