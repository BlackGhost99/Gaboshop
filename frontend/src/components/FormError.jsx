/** Erreur d'un formulaire : ce qui s'est passé, pourquoi, et quoi faire (voir utils/feedback.describeError). */
export default function FormError({ error }) {
  if (!error) return null;
  const info = typeof error === 'string' ? { message: error } : error;
  return (
    <div role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
      <p className="font-semibold">{info.message}</p>
      {info.reason && <p className="mt-1">{info.reason}</p>}
      {info.nextStep && <p className="mt-1 text-red-700">{info.nextStep}</p>}
    </div>
  );
}
