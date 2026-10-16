import { useCallback, useEffect, useState } from 'react';
import { notifyError, notifySuccess, notifyWarning } from '../utils/feedback';
import { sendTestPush } from '../services/notificationService';
import { disablePush, enablePush, getPushState, pushErrorText } from '../utils/push';

// État des alertes sur cet appareil, et les gestes pour les activer, les couper ou les essayer.
export default function usePushDevice() {
  const [state, setState] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setState(await getPushState());
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const enable = useCallback(async () => {
    setBusy(true);
    try {
      await enablePush();
      notifySuccess('Alertes activées', 'Vous serez prévenu sur cet appareil à chaque nouveauté, même quand Gaboshop est fermé.');
      return true;
    } catch (error) {
      const text = pushErrorText(error);
      notifyWarning(text.message, text.nextStep);
      return false;
    } finally {
      await refresh();
      setBusy(false);
    }
  }, [refresh]);

  const disable = useCallback(async () => {
    setBusy(true);
    await disablePush();
    await refresh();
    setBusy(false);
    notifySuccess('Alertes coupées', 'Cet appareil ne sera plus alerté. Vos notifications restent dans la cloche.');
  }, [refresh]);

  const test = useCallback(async () => {
    setBusy(true);
    try {
      const result = await sendTestPush();
      if (result.delivered > 0) {
        notifySuccess('Alerte envoyée', `Elle doit s’afficher dans quelques secondes (${result.delivered} appareil${result.delivered > 1 ? 's' : ''}).`);
      } else {
        notifyWarning('L’alerte n’a pas pu être remise', 'Vérifiez que les notifications sont autorisées pour ce site dans les réglages de l’appareil, puis réessayez.');
      }
    } catch (error) {
      notifyError(error, { action: 'Essayer les alertes' });
    } finally {
      setBusy(false);
    }
  }, []);

  return { state, busy, enable, disable, test };
}

