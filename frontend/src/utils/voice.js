// Mode vocal de l'assistant : écouter (parole → texte) et parler (texte → voix).
// Dans l'appli Android, on passe par les services vocaux du téléphone (plugins
// Capacitor) ; sur le site web, par la reconnaissance vocale du navigateur.
import { SpeechRecognition as NativeSpeech } from '@capacitor-community/speech-recognition';
import { TextToSpeech } from '@capacitor-community/text-to-speech';

const LANG = 'fr-FR';
const isNative = () => Boolean(window.Capacitor?.isNativePlatform?.());
const WebRecognition = () => window.SpeechRecognition || window.webkitSpeechRecognition;

export const canListen = () => isNative() || Boolean(WebRecognition());
export const canSpeak = () => isNative() || 'speechSynthesis' in window;

let webRecognizer = null;

// Écoute une phrase et renvoie le texte reconnu ('' si rien).
export const listenOnce = async () => {
  if (isNative()) {
    const { available } = await NativeSpeech.available();
    if (!available) throw new Error("La reconnaissance vocale n'est pas disponible sur ce téléphone.");
    const perm = await NativeSpeech.requestPermissions();
    if (perm.speechRecognition !== 'granted') throw new Error('Autorisez le micro pour parler à l’assistant.');
    const result = await NativeSpeech.start({ language: LANG, maxResults: 1, partialResults: false, popup: false });
    return (result?.matches?.[0] || '').trim();
  }
  const Recognition = WebRecognition();
  if (!Recognition) throw new Error("Votre navigateur ne permet pas la dictée vocale. Essayez Chrome ou l'appli.");
  return new Promise((resolve, reject) => {
    const rec = new Recognition();
    webRecognizer = rec;
    rec.lang = LANG;
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    let text = '';
    rec.onresult = (e) => { text = e.results?.[0]?.[0]?.transcript || ''; };
    rec.onerror = (e) => {
      if (e.error === 'no-speech' || e.error === 'aborted') resolve('');
      else if (e.error === 'not-allowed') reject(new Error('Autorisez le micro pour parler à l’assistant.'));
      else reject(new Error('Le micro ne répond pas, réessayez.'));
    };
    rec.onend = () => { webRecognizer = null; resolve(text.trim()); };
    rec.start();
  });
};

export const stopListening = async () => {
  try {
    if (isNative()) await NativeSpeech.stop();
    else webRecognizer?.stop();
  } catch {
    // déjà arrêté
  }
};

// Nettoie le texte avant lecture (symboles, puces, montants lisibles).
const forSpeech = (text) => String(text || '')
  .replace(/[*_#>`•]/g, ' ')
  .replace(/FCFA/g, 'francs CFA')
  .replace(/\s+/g, ' ')
  .trim();

// Lit le texte à voix haute ; la promesse se termine à la fin de la lecture.
export const speak = async (text) => {
  const clean = forSpeech(text);
  if (!clean) return;
  if (isNative()) {
    await TextToSpeech.speak({ text: clean, lang: LANG, rate: 1.0, pitch: 1.0, volume: 1.0 });
    return;
  }
  if (!('speechSynthesis' in window)) return;
  await new Promise((resolve) => {
    const utter = new SpeechSynthesisUtterance(clean);
    utter.lang = LANG;
    const voice = window.speechSynthesis.getVoices().find((v) => v.lang?.startsWith('fr'));
    if (voice) utter.voice = voice;
    utter.onend = resolve;
    utter.onerror = resolve;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utter);
  });
};

export const stopSpeaking = async () => {
  try {
    if (isNative()) await TextToSpeech.stop();
    else window.speechSynthesis?.cancel();
  } catch {
    // rien à arrêter
  }
};
