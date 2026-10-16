import api from '../services/api';
import { notifyError } from './feedback';

/** Ouvre la facture PDF Gaboshop de la commande (téléchargée si l'appareil ne sait pas l'afficher). */
export async function openInvoice(orderId, orderNumber) {
  try {
    const res = await api.get(`/orders/${orderId}/invoice/`, { responseType: 'blob' });
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `Facture-${orderNumber || orderId}.pdf`;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (err) {
    notifyError(err, { action: 'Ouvrir la facture' });
  }
}
