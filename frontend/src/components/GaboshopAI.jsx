import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAIContext } from '../context/AIContext';
import { formatCurrency } from '../utils/helpers';
import { isLoggedIn, addToCart, savePendingCartItem } from '../utils/session';
import { canListen, canSpeak, listenOnce, speak, stopListening, stopSpeaking } from '../utils/voice';

// Suggestions adaptées à l'espace où se trouve l'utilisateur
const SUGGESTIONS = {
    store: ['Résume ma boutique', 'Commandes à préparer', 'Produits en stock faible', 'Comment vendre plus ?'],
    delivery: ['Mes livraisons en cours', 'Livraisons disponibles', 'Par où commencer ?'],
    admin: ['Chiffres de la semaine', 'Commerces à vérifier', 'Dernières commandes'],
    shop: ['Je cherche des baskets', 'Riz moins de 5000 F', 'Mon panier', 'Comment se passe la livraison ?'],
};

const spaceOf = (path) => {
    if (path.startsWith('/store')) return 'store';
    if (path.startsWith('/delivery')) return 'delivery';
    if (path.startsWith('/admin')) return 'admin';
    return 'shop';
};

const GaboshopAI = () => {
    const { messages, isLoading, sendMessage, confirmAction, addBotMessage } = useAIContext();
    const [isOpen, setIsOpen] = useState(false);
    const [inputValue, setInputValue] = useState('');
    const [doneTokens, setDoneTokens] = useState({});
    // Mode vocal : 'off' | 'listening' | 'thinking' | 'speaking'
    const [voiceState, setVoiceState] = useState('off');
    const [readAloud, setReadAloud] = useState(() => {
        try { return localStorage.getItem('gaboshop_ai_voice') === '1'; } catch { return false; }
    });
    const [handsFree, setHandsFree] = useState(false);
    const voiceLoop = useRef(false);
    const messagesEndRef = useRef(null);
    const navigate = useNavigate();
    const location = useLocation();
    const space = spaceOf(location.pathname);
    const next = encodeURIComponent(`${location.pathname}${location.search}`);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isOpen]);

    const toggleReadAloud = () => {
        const next = !readAloud;
        setReadAloud(next);
        try { localStorage.setItem('gaboshop_ai_voice', next ? '1' : '0'); } catch { /* ignoré */ }
        if (!next) stopSpeaking();
    };

    const handleSend = async (text) => {
        const message = (text ?? inputValue).trim();
        if (!message || isLoading) return;
        setInputValue('');
        const reply = await sendMessage(message);
        if (readAloud && reply && canSpeak()) {
            setVoiceState('speaking');
            await speak(reply);
            setVoiceState('off');
        }
    };

    // Parler à l'assistant : il écoute, répond à voix haute, et en mode
    // « conversation » il réécoute tout seul jusqu'à ce qu'on se taise.
    const talk = async (continuous = handsFree) => {
        if (voiceState !== 'off') {
            voiceLoop.current = false;
            await stopListening();
            await stopSpeaking();
            setVoiceState('off');
            return;
        }
        voiceLoop.current = true;
        try {
            do {
                setVoiceState('listening');
                const heard = await listenOnce();
                if (!heard || !voiceLoop.current) break;
                setVoiceState('thinking');
                const reply = await sendMessage(heard);
                if (!voiceLoop.current) break;
                if (reply && canSpeak()) {
                    setVoiceState('speaking');
                    await speak(reply);
                }
            } while (continuous && voiceLoop.current);
        } catch (err) {
            addBotMessage(err.message || 'Le micro ne répond pas.', { isError: true });
        } finally {
            voiceLoop.current = false;
            setVoiceState('off');
        }
    };

    const closeChat = () => {
        voiceLoop.current = false;
        stopListening();
        stopSpeaking();
        setVoiceState('off');
        setIsOpen(false);
    };

    const openProduct = (product) => {
        setIsOpen(false);
        navigate(`/stores/${product.store}?product=${product.id}`);
    };

    const quickAdd = (product) => {
        if (!isLoggedIn()) {
            savePendingCartItem(product);
            addBotMessage(`Connectez-vous ou créez un compte pour ajouter ${product.name} : il sera ajouté juste après.`, { loginPrompt: true });
            return;
        }
        addToCart(product, 1);
        addBotMessage(`${product.name} ajouté à votre panier.`, { cartChanged: true });
    };

    const handleConfirm = async (token, accept) => {
        setDoneTokens((prev) => ({ ...prev, [token]: accept ? 'pending' : 'cancelled' }));
        if (!accept) {
            addBotMessage('Modification annulée.');
            return;
        }
        const ok = await confirmAction(token);
        setDoneTokens((prev) => ({ ...prev, [token]: ok ? 'done' : 'failed' }));
    };

    return (
        <div className="fixed bottom-6 right-4 sm:right-6 z-50 font-sans">
            {isOpen && (
                <div className="bg-white shadow-2xl rounded-2xl w-[calc(100vw-2rem)] max-w-sm sm:w-96 flex flex-col mb-4 overflow-hidden ring-1 ring-black/5 max-h-[75dvh]">
                    {/* En-tête */}
                    <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-4 flex justify-between items-center">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
                                <span className="text-xl">🤖</span>
                            </div>
                            <div>
                                <h3 className="text-white font-bold text-sm">Gaboshop AI</h3>
                                <p className="text-indigo-100 text-xs flex items-center gap-1">
                                    <span className={`w-2 h-2 rounded-full animate-pulse ${isLoading ? 'bg-yellow-400' : 'bg-green-400'}`}></span>
                                    {isLoading ? 'Je m\'en occupe…' : 'En ligne'}
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-1">
                        {canSpeak() && (
                            <button
                                onClick={toggleReadAloud}
                                className={`text-xs px-2 py-1 rounded-full ${readAloud ? 'bg-white text-indigo-700' : 'bg-white/20 text-white'}`}
                                aria-label={readAloud ? 'Ne plus lire les réponses' : 'Lire les réponses à voix haute'}
                                title="Lecture à voix haute"
                            >
                                {readAloud ? '🔊' : '🔈'}
                            </button>
                        )}
                        {canListen() && (
                            <button
                                onClick={() => setHandsFree((v) => !v)}
                                className={`text-xs px-2 py-1 rounded-full ${handsFree ? 'bg-white text-indigo-700' : 'bg-white/20 text-white'}`}
                                aria-label="Mode conversation mains libres"
                                title="Conversation mains libres"
                            >
                                {handsFree ? '🎙️ Conversation' : '🎙️'}
                            </button>
                        )}
                        <button onClick={closeChat} className="text-white/80 hover:text-white" aria-label="Fermer">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                        </div>
                    </div>

                    {voiceState !== 'off' && (
                        <div className="bg-indigo-50 text-indigo-800 text-xs px-4 py-2 flex items-center justify-between">
                            <span>
                                {voiceState === 'listening' && '🎙️ Je vous écoute…'}
                                {voiceState === 'thinking' && '💭 Je réfléchis…'}
                                {voiceState === 'speaking' && '🔊 Je vous réponds…'}
                            </span>
                            <button onClick={() => talk()} className="font-semibold underline">Arrêter</button>
                        </div>
                    )}

                    {/* Messages */}
                    <div className="flex-1 min-h-[16rem] overflow-y-auto p-4 space-y-3 bg-slate-50">
                        {messages.length === 0 && (
                            <div className="text-center text-gray-500 text-sm py-4">
                                <p className="mb-2">Bonjour ! Je suis l'assistant Gaboshop.</p>
                                <p>
                                    {space === 'shop' && 'Dites-moi ce que vous cherchez : je trouve, je compare et je mets au panier.'}
                                    {space === 'store' && 'Je peux suivre vos commandes, votre stock et vos prix.'}
                                    {space === 'delivery' && 'Je peux organiser vos livraisons.'}
                                    {space === 'admin' && 'Je peux vous donner les chiffres et les points à surveiller.'}
                                </p>
                            </div>
                        )}

                        {messages.map((msg) => (
                            <div key={msg.id} className={`flex flex-col ${msg.type === 'user' ? 'items-end' : 'items-start'}`}>
                                <div className={`max-w-[85%] whitespace-pre-line rounded-2xl px-4 py-2 text-sm shadow-sm ${
                                    msg.type === 'user'
                                        ? 'bg-indigo-600 text-white rounded-br-none'
                                        : msg.isError
                                        ? 'bg-red-50 text-red-800 border border-red-200 rounded-bl-none'
                                        : 'bg-white text-gray-800 border border-gray-100 rounded-bl-none'
                                }`}>
                                    {msg.text}
                                </div>

                                {msg.products?.length > 0 && (
                                    <div className="mt-2 w-full space-y-2">
                                        {msg.products.map((p) => (
                                            <div key={p.id} className="w-full flex items-center gap-2 bg-white border border-gray-100 rounded-xl p-2 shadow-sm">
                                                <button type="button" onClick={() => openProduct(p)} className="flex items-center gap-3 flex-1 min-w-0 text-left">
                                                    <img
                                                        src={p.image || '/placeholder.svg'}
                                                        alt=""
                                                        className="w-12 h-12 rounded-lg object-cover bg-gray-100 flex-shrink-0"
                                                        onError={(e) => { e.currentTarget.src = '/placeholder.svg'; }}
                                                    />
                                                    <span className="flex-1 min-w-0">
                                                        <span className="block text-sm font-semibold text-gray-900 truncate">
                                                            {p.name}{p.brand ? ` · ${p.brand}` : ''}
                                                        </span>
                                                        <span className="block text-xs text-gray-500 truncate">
                                                            {p.store_name}{p.stock <= 0 ? ' · rupture' : ''}{p.sizes ? ` · tailles ${p.sizes}` : ''}
                                                        </span>
                                                        <span className="block text-sm font-bold text-indigo-700">{formatCurrency(p.price)}</span>
                                                    </span>
                                                </button>
                                                {space === 'shop' && p.stock > 0 && (
                                                    <button
                                                        type="button"
                                                        onClick={() => quickAdd(p)}
                                                        className="flex-shrink-0 text-xs font-semibold bg-indigo-600 text-white rounded-lg px-2.5 py-2"
                                                    >
                                                        + Panier
                                                    </button>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {msg.confirmations?.map((c) => (
                                    <div key={c.token} className="mt-2 w-full bg-amber-50 border border-amber-200 rounded-xl p-3 text-sm">
                                        <p className="text-amber-900 font-medium">{c.label}</p>
                                        {doneTokens[c.token] ? (
                                            <p className="text-xs text-amber-800 mt-2">
                                                {{ pending: 'En cours…', done: 'Confirmé ✓', failed: 'Échec', cancelled: 'Annulé' }[doneTokens[c.token]]}
                                            </p>
                                        ) : (
                                            <div className="flex gap-2 mt-2">
                                                <button onClick={() => handleConfirm(c.token, true)} className="flex-1 bg-amber-600 text-white rounded-lg py-2 font-semibold">Confirmer</button>
                                                <button onClick={() => handleConfirm(c.token, false)} className="flex-1 border border-amber-300 text-amber-900 rounded-lg py-2">Annuler</button>
                                            </div>
                                        )}
                                    </div>
                                ))}

                                {msg.loginPrompt && (
                                    <div className="mt-2 flex gap-2">
                                        <Link to={`/login?next=${next}`} onClick={closeChat} className="text-xs font-semibold bg-slate-900 text-white rounded-lg px-3 py-2">Se connecter</Link>
                                        <Link to={`/register?next=${next}`} onClick={() => setIsOpen(false)} className="text-xs font-semibold border border-slate-300 text-slate-900 rounded-lg px-3 py-2">Créer un compte</Link>
                                    </div>
                                )}

                                {msg.link && (
                                    <Link to={msg.link.path} onClick={() => setIsOpen(false)} className="mt-2 text-xs font-semibold text-indigo-700 underline">
                                        {msg.link.label}
                                    </Link>
                                )}

                                {msg.cartChanged && (
                                    <Link to="/client/dashboard" onClick={() => setIsOpen(false)} className="mt-2 text-xs font-semibold text-indigo-700 underline">
                                        Voir mon panier et commander
                                    </Link>
                                )}
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

                    {messages.length === 0 && !isLoading && (
                        <div className="px-4 py-2 bg-slate-50">
                            <div className="flex flex-wrap gap-2">
                                {SUGGESTIONS[space].map((suggestion) => (
                                    <button
                                        key={suggestion}
                                        onClick={() => handleSend(suggestion)}
                                        className="text-xs px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full hover:bg-indigo-100 transition-colors"
                                    >
                                        {suggestion}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    <form
                        className="p-3 bg-white border-t border-gray-100 flex gap-2"
                        onSubmit={(e) => { e.preventDefault(); handleSend(); }}
                    >
                        <input
                            type="text"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            placeholder="Écrivez votre demande…"
                            disabled={isLoading}
                            className="flex-1 bg-gray-100 border-0 rounded-full px-4 py-2 text-sm focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                        />
                        {canListen() && !inputValue.trim() ? (
                            <button
                                type="button"
                                onClick={() => talk()}
                                className={`rounded-full p-2 flex-shrink-0 text-white ${voiceState === 'listening' ? 'bg-red-500 animate-pulse' : 'bg-indigo-600 hover:bg-indigo-700'}`}
                                aria-label={voiceState === 'off' ? 'Parler à l’assistant' : 'Arrêter'}
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18.5a6.5 6.5 0 006.5-6.5M12 18.5A6.5 6.5 0 015.5 12M12 18.5V22m-3.5 0h7M12 15a3 3 0 003-3V5a3 3 0 10-6 0v7a3 3 0 003 3z" />
                                </svg>
                            </button>
                        ) : (
                        <button
                            type="submit"
                            disabled={isLoading || !inputValue.trim()}
                            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-full p-2 flex-shrink-0"
                            aria-label="Envoyer"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                            </svg>
                        </button>
                        )}
                    </form>
                </div>
            )}

            {!isOpen && (
                <button
                    onClick={() => setIsOpen(true)}
                    className="flex items-center justify-center w-14 h-14 bg-gradient-to-br from-indigo-600 to-purple-600 text-white rounded-full shadow-lg hover:scale-110 transition-all duration-300"
                    aria-label="Ouvrir l'assistant"
                >
                    <span className="text-2xl">🤖</span>
                </button>
            )}
        </div>
    );
};

export default GaboshopAI;
