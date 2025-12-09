import { useState, useEffect } from 'react';
import { uploadProof, verifyPIN } from '../services/deliveryService';

/**
 * Modal pour uploader la preuve de livraison
 * PHASE 3: Photo pièce d'identité OBLIGATOIRE + GPS + Signature/PIN
 * 
 * Justification: Toutes les routes ne sont pas accessibles à Libreville,
 * le client peut venir chercher le colis. La photo de la pièce d'identité
 * garantit que c'est bien le bon destinataire.
 */
export default function ProofUploadModal({ delivery, onClose, onSuccess }) {
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [step, setStep] = useState(1); // 1: Photos+GPS, 2: Verification (Signature/PIN)
  
  // Step 1: Photos + GPS
  const [idCardPhoto, setIdCardPhoto] = useState(null);
  const [idCardPreview, setIdCardPreview] = useState(null);
  const [packagePhoto, setPackagePhoto] = useState(null);
  const [packagePreview, setPackagePreview] = useState(null);
  const [gpsLocation, setGpsLocation] = useState(null);
  const [gpsLoading, setGpsLoading] = useState(false);
  
  // Step 2: Verification
  const [verificationMethod, setVerificationMethod] = useState('signature'); // 'signature' or 'pin'
  const [signature, setSignature] = useState(null);
  const [signaturePreview, setSignaturePreview] = useState(null);
  const [pinCode, setPinCode] = useState('');
  const [pinVerified, setPinVerified] = useState(false);

  // Get GPS location automatically
  useEffect(() => {
    setGpsLoading(true);
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setGpsLocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy
          });
          setGpsLoading(false);
        },
        (error) => {
          console.error('Erreur GPS:', error);
          setGpsLoading(false);
          setErrors(prev => ({ ...prev, gps: 'Impossible d\'obtenir la position GPS' }));
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    } else {
      setGpsLoading(false);
      setErrors(prev => ({ ...prev, gps: 'GPS non disponible sur cet appareil' }));
    }
  }, []);

  const handleIdCardChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setIdCardPhoto(file);
      setIdCardPreview(URL.createObjectURL(file));
      setErrors(prev => ({ ...prev, id_card_photo: null }));
    }
  };

  const handlePackagePhotoChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setPackagePhoto(file);
      setPackagePreview(URL.createObjectURL(file));
    }
  };

  const handleSignatureChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSignature(file);
      setSignaturePreview(URL.createObjectURL(file));
      setErrors(prev => ({ ...prev, signature: null }));
    }
  };

  const handleVerifyPIN = async () => {
    if (!pinCode || pinCode.length < 4) {
      setErrors(prev => ({ ...prev, pin: 'Le PIN doit contenir au moins 4 chiffres' }));
      return;
    }

    setLoading(true);
    const response = await verifyPIN(delivery.id, pinCode);
    setLoading(false);

    console.log('Vérification PIN response:', response);
    if (response.success) {
      console.log('PIN vérifié! Mise à jour de pinVerified à true');
      setPinVerified(true);
      setErrors(prev => ({ ...prev, pin: null }));
      
      // Afficher un message de succès avec feedback visuel
      console.log('✓ Code PIN accepté - Vous pouvez maintenant soumettre la preuve');
    } else {
      console.log('PIN incorrect:', response.error);
      setErrors(prev => ({ ...prev, pin: response.error || 'PIN incorrect' }));
    }
  };

  const handleNextStep = () => {
    const newErrors = {};

    // Validate Step 1
    if (!idCardPhoto) {
      newErrors.id_card_photo = 'La photo de la pièce d\'identité est OBLIGATOIRE';
    }
    if (!gpsLocation) {
      newErrors.gps = 'La position GPS est requise';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setStep(2);
  };

  const handleSubmit = async () => {
    const newErrors = {};

    // Validate verification method
    if (verificationMethod === 'signature' && !signature) {
      newErrors.signature = 'La signature du client est requise';
    }
    if (verificationMethod === 'pin' && !pinVerified) {
      newErrors.pin = 'Veuillez vérifier le code PIN du client';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    // Prepare FormData
    const formData = new FormData();
    formData.append('id_card_photo', idCardPhoto); // OBLIGATOIRE
    if (packagePhoto) {
      formData.append('package_photo', packagePhoto); // OPTIONNELLE
    }
    formData.append('latitude', gpsLocation.latitude);
    formData.append('longitude', gpsLocation.longitude);
    
    if (verificationMethod === 'signature') {
      formData.append('signature', signature);
    } else {
      formData.append('pin_code', pinCode);
      formData.append('pin_verified', true);
    }

    formData.append('client_received_status', true);

    setLoading(true);
    const response = await uploadProof(delivery.id, formData);
    setLoading(false);

    if (response.success) {
      onSuccess();
    } else {
      setErrors(response.validation_errors || { general: response.error });
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-900">
            Preuve de livraison - Commande #{delivery.order_id}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Progress Indicator */}
        <div className="flex items-center mb-6">
          <div className={`flex items-center ${step >= 1 ? 'text-blue-600' : 'text-gray-400'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 1 ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}>
              1
            </div>
            <span className="ml-2 text-sm font-medium">Photos + GPS</span>
          </div>
          <div className="flex-1 h-1 mx-4 bg-gray-200">
            <div className={`h-1 ${step >= 2 ? 'bg-blue-600' : 'bg-gray-200'} transition-all`} style={{ width: step >= 2 ? '100%' : '0%' }} />
          </div>
          <div className={`flex items-center ${step >= 2 ? 'text-blue-600' : 'text-gray-400'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 2 ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}>
              2
            </div>
            <span className="ml-2 text-sm font-medium">Vérification</span>
          </div>
        </div>

        {errors.general && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
            {errors.general}
          </div>
        )}

        {/* Step 1: Photos + GPS */}
        {step === 1 && (
          <div className="space-y-6">
            {/* ID Card Photo - OBLIGATOIRE */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                📸 Photo de la pièce d'identité du client <span className="text-red-600">*</span>
              </label>
              <p className="text-xs text-gray-500 mb-3">
                Obligatoire: Certaines routes ne sont pas accessibles, le client peut venir chercher le colis.
                La pièce d'identité garantit que c'est bien le bon destinataire.
              </p>
              <input
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleIdCardChange}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
              {idCardPreview && (
                <img src={idCardPreview} alt="Pièce d'identité" className="mt-3 w-full h-48 object-cover rounded-md border border-gray-200" />
              )}
              {errors.id_card_photo && (
                <p className="mt-1 text-sm text-red-600">{errors.id_card_photo}</p>
              )}
            </div>

            {/* Package Photo - OPTIONNELLE */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                📦 Photo du colis (optionnelle)
              </label>
              <p className="text-xs text-gray-500 mb-3">
                Si la livraison se fait au domicile du client, vous pouvez ajouter une photo du colis.
              </p>
              <input
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handlePackagePhotoChange}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-gray-50 file:text-gray-700 hover:file:bg-gray-100"
              />
              {packagePreview && (
                <img src={packagePreview} alt="Colis" className="mt-3 w-full h-48 object-cover rounded-md border border-gray-200" />
              )}
            </div>

            {/* GPS Location */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                📍 Position GPS <span className="text-red-600">*</span>
              </label>
              {gpsLoading ? (
                <div className="flex items-center text-sm text-gray-600">
                  <svg className="animate-spin h-5 w-5 mr-2 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Récupération de la position GPS...
                </div>
              ) : gpsLocation ? (
                <div className="p-3 bg-green-50 border border-green-200 rounded-md">
                  <p className="text-sm text-green-700">✓ Position GPS obtenue</p>
                  <p className="text-xs text-gray-600 mt-1">
                    Lat: {gpsLocation.latitude.toFixed(6)}, Long: {gpsLocation.longitude.toFixed(6)}
                  </p>
                  <p className="text-xs text-gray-500">Précision: ±{gpsLocation.accuracy.toFixed(0)}m</p>
                </div>
              ) : (
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                  <p className="text-sm text-yellow-700">⚠ GPS non disponible</p>
                </div>
              )}
              {errors.gps && (
                <p className="mt-1 text-sm text-red-600">{errors.gps}</p>
              )}
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
              >
                Annuler
              </button>
              <button
                onClick={handleNextStep}
                disabled={!idCardPhoto || !gpsLocation}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Suivant →
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Verification */}
        {step === 2 && (
          <div className="space-y-6">
            {/* Verification Method Selection */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-3">
                Méthode de vérification <span className="text-red-600">*</span>
              </label>
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={() => setVerificationMethod('signature')}
                  className={`p-4 border-2 rounded-lg text-left transition ${
                    verificationMethod === 'signature'
                      ? 'border-blue-600 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="text-2xl mb-2">✍️</div>
                  <div className="font-semibold text-gray-900">Signature</div>
                  <div className="text-xs text-gray-600 mt-1">Le client signe pour confirmer</div>
                </button>
                <button
                  onClick={() => setVerificationMethod('pin')}
                  className={`p-4 border-2 rounded-lg text-left transition ${
                    verificationMethod === 'pin'
                      ? 'border-blue-600 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="text-2xl mb-2">🔢</div>
                  <div className="font-semibold text-gray-900">Code PIN</div>
                  <div className="text-xs text-gray-600 mt-1">Le client fournit son code PIN</div>
                </button>
              </div>
            </div>

            {/* Signature Upload */}
            {verificationMethod === 'signature' && (
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  ✍️ Signature du client <span className="text-red-600">*</span>
                </label>
                <input
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={handleSignatureChange}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
                {signaturePreview && (
                  <img src={signaturePreview} alt="Signature" className="mt-3 w-full h-32 object-contain bg-gray-50 rounded-md border border-gray-200" />
                )}
                {errors.signature && (
                  <p className="mt-1 text-sm text-red-600">{errors.signature}</p>
                )}
              </div>
            )}

            {/* PIN Verification */}
            {verificationMethod === 'pin' && (
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  🔢 Code PIN du client (4-6 chiffres) <span className="text-red-600">*</span>
                </label>
                <div className={`p-4 rounded-lg border-2 transition ${
                  pinVerified 
                    ? 'bg-green-50 border-green-300' 
                    : 'bg-white border-gray-300'
                }`}>
                  <div className="flex space-x-2 mb-3">
                    <input
                      type="text"
                      maxLength="6"
                      pattern="[0-9]*"
                      inputMode="numeric"
                      value={pinCode}
                      onChange={(e) => setPinCode(e.target.value.replace(/\D/g, ''))}
                      disabled={pinVerified}
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                      placeholder="0000"
                    />
                    {!pinVerified ? (
                      <button
                        onClick={handleVerifyPIN}
                        disabled={loading || pinCode.length < 4}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition"
                      >
                        {loading ? 'Vérification...' : 'Vérifier'}
                      </button>
                    ) : (
                      <div className="px-4 py-2 bg-green-600 text-white rounded-md font-semibold flex items-center justify-center min-w-max">
                        ✓ Vérifié
                      </div>
                    )}
                  </div>
                  
                  {errors.pin && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                      <p className="text-sm text-red-700 font-medium">{errors.pin}</p>
                      <p className="text-xs text-red-600 mt-1">Veuillez vérifier le code et réessayer</p>
                    </div>
                  )}
                  
                  {pinVerified && (
                    <div className="p-3 bg-green-100 border border-green-300 rounded-md">
                      <p className="text-sm text-green-700 font-semibold">✓ Code PIN vérifié avec succès</p>
                      <p className="text-xs text-green-600 mt-1">Vous pouvez maintenant confirmer la livraison</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="flex justify-between space-x-3">
              <button
                onClick={() => setStep(1)}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 font-medium transition"
              >
                ← Retour
              </button>
              <button
                onClick={handleSubmit}
                disabled={loading || (verificationMethod === 'signature' && !signature) || (verificationMethod === 'pin' && !pinVerified)}
                className={`px-8 py-3 rounded-md font-bold text-base transition transform ${
                  loading || (verificationMethod === 'signature' && !signature) || (verificationMethod === 'pin' && !pinVerified)
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed opacity-60'
                    : 'bg-green-600 text-white hover:bg-green-700 active:scale-95 shadow-lg hover:shadow-xl'
                }`}
              >
                {loading ? '⏳ Upload en cours...' : '✓ Confirmer la livraison'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
