import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import { updateStoreMarketMode } from '../services/adminService';

const StoreMarketModeModal = ({ isOpen, onClose, store, onSuccess }) => {
  const resolveMode = (storeData) => storeData?.market_mode || (storeData?.is_b2b ? 'b2b' : 'b2c');
  const [marketMode, setMarketMode] = useState(resolveMode(store));
  const [minOrderAmount, setMinOrderAmount] = useState(store?.b2b_min_order_amount || 0);
  const [deliveryDelay, setDeliveryDelay] = useState(store?.b2b_delivery_delay || 24);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (store) {
      setMarketMode(resolveMode(store));
      setMinOrderAmount(store.b2b_min_order_amount || 0);
      setDeliveryDelay(store.b2b_delivery_delay || 24);
    }
  }, [store]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const payload = {
        market_mode: marketMode,
      };

      if (marketMode === 'b2b') {
        payload.b2b_min_order_amount = minOrderAmount;
        payload.b2b_delivery_delay = deliveryDelay;
      }

      const res = await updateStoreMarketMode(store.id, payload);

      if (res?.success) {
        setSuccess(true);
        if (onSuccess) {
          onSuccess();
        }
        setTimeout(() => {
          onClose();
          setSuccess(false);
        }, 2000);
      } else {
        setError(res?.error || res?.message || 'Update failed');
      }
    } catch (err) {
      setError(err?.message || 'Update failed');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !store) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Store mode - ${store.name}`}
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded text-sm">
            <div className="font-semibold mb-1">Settings updated</div>
            {marketMode === 'b2b' && (
              <div className="text-xs mt-1 text-green-600">
                B2B profile enabled for this store.
              </div>
            )}
          </div>
        )}

        <div className="bg-gray-50 rounded-lg p-4 space-y-3">
          <div className="text-sm font-semibold text-gray-900">Market mode</div>
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="radio"
              name="market-mode"
              value="b2c"
              checked={marketMode === 'b2c'}
              onChange={() => setMarketMode('b2c')}
              className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
            />
            <div>
              <span className="text-sm font-semibold text-gray-900">B2C</span>
              <p className="text-xs text-gray-600 mt-0.5">
                Sell to final customers
              </p>
            </div>
          </label>
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="radio"
              name="market-mode"
              value="b2b"
              checked={marketMode === 'b2b'}
              onChange={() => setMarketMode('b2b')}
              className="w-4 h-4 text-purple-600 border-gray-300 focus:ring-purple-500"
            />
            <div>
              <span className="text-sm font-semibold text-gray-900">B2B</span>
              <p className="text-xs text-gray-600 mt-0.5">
                Sell wholesale to other stores
              </p>
            </div>
          </label>
        </div>

        {marketMode === 'b2b' && (
          <>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Min order amount (FCFA)
              </label>
              <input
                type="number"
                min="0"
                step="1"
                value={minOrderAmount}
                onChange={(e) => setMinOrderAmount(parseFloat(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                placeholder="0"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Delivery delay (hours)
              </label>
              <input
                type="number"
                min="1"
                step="1"
                value={deliveryDelay}
                onChange={(e) => setDeliveryDelay(parseInt(e.target.value, 10) || 24)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                placeholder="24"
              />
            </div>

            <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
              <p className="text-xs text-purple-800">
                B2B stores appear in procurement catalogs for other stores.
              </p>
            </div>
          </>
        )}

        <div className="flex gap-3 pt-4 border-t border-gray-200">
          <button
            type="submit"
            disabled={loading || success}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Saving...' : success ? 'Saved' : 'Save'}
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default StoreMarketModeModal;
