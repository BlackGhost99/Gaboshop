import React, { useEffect, useMemo } from 'react';
import { MAX_EXTRA_PHOTOS, extraPhotos } from '../utils/productPhotos';

function FilePreview({ file, onRemove }) {
  const url = useMemo(() => URL.createObjectURL(file), [file]);
  useEffect(() => () => URL.revokeObjectURL(url), [url]);
  return <Thumb src={url} label={file.name} onRemove={onRemove} />;
}

function Thumb({ src, label, onRemove }) {
  return (
    <div className="relative h-20 w-20 flex-shrink-0 overflow-hidden rounded border bg-gray-50">
      {src && <img src={src} alt={label} className="h-full w-full object-cover" />}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label="Retirer cette photo"
          className="absolute right-0.5 top-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-black/60 text-sm text-white"
        >
          ✕
        </button>
      )}
    </div>
  );
}

/**
 * Photos d'un produit : une photo principale (vue dans le catalogue) et jusqu'à 5 autres
 * (vues en ouvrant le produit).
 */
export default function ProductPhotosField({ product, mainFile, onMainFile, galleryFiles, onGalleryFiles, removed, onRemoved }) {
  const kept = extraPhotos(product).filter((p) => !removed.includes(p.key));
  const left = MAX_EXTRA_PHOTOS - kept.length - galleryFiles.length;

  const addFiles = (e) => {
    const picked = Array.from(e.target.files || []);
    e.target.value = '';
    onGalleryFiles([...galleryFiles, ...picked.slice(0, Math.max(left, 0))]);
  };

  return (
    <div className="mb-4 space-y-3">
      <div>
        <label className="mb-1 block text-sm font-medium">Photo principale</label>
        <div className="flex items-center gap-3">
          {mainFile ? (
            <FilePreview file={mainFile} onRemove={() => onMainFile(null)} />
          ) : (
            product?.image && <Thumb src={product.image} label="Photo principale" />
          )}
          <input type="file" accept="image/*" className="w-full rounded border p-2 text-sm" onChange={(e) => onMainFile(e.target.files[0] || null)} />
        </div>
        <p className="mt-1 text-xs text-gray-500">
          C’est elle qu’on voit dans le catalogue.{product?.image && !mainFile ? ' Laissez vide pour la garder.' : ''}
        </p>
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium">Autres photos ({kept.length + galleryFiles.length}/{MAX_EXTRA_PHOTOS})</label>
        <div className="flex flex-wrap gap-2">
          {kept.map((p) => (
            <Thumb key={p.key} src={p.src} label="Photo du produit" onRemove={() => onRemoved([...removed, p.key])} />
          ))}
          {galleryFiles.map((file, i) => (
            <FilePreview key={`${file.name}-${i}`} file={file} onRemove={() => onGalleryFiles(galleryFiles.filter((_, j) => j !== i))} />
          ))}
          {left > 0 && (
            <label className="flex h-20 w-20 flex-shrink-0 cursor-pointer flex-col items-center justify-center rounded border-2 border-dashed text-center text-xs text-gray-500 hover:border-indigo-400 hover:text-indigo-600">
              <span className="text-xl leading-none">+</span>
              Ajouter
              <input type="file" accept="image/*" multiple className="hidden" onChange={addFiles} />
            </label>
          )}
        </div>
        <p className="mt-1 text-xs text-gray-500">Montrez le produit sous plusieurs angles, de près, porté ou en situation. On les voit en ouvrant le produit.</p>
      </div>
    </div>
  );
}
