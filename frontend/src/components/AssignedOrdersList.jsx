import React, { useState, useEffect } from 'react';
import { getAssignedOrders, acceptDelivery, rejectDelivery } from '../services/deliveryService';
import { formatCurrency } from '../utils/helpers';

const AssignedOrdersList = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState({});
  const [filterStatus, setFilterStatus] = useState('all');

  useEffect(() => {
    fetchAssignedOrders();
  }, []);

  const fetchAssignedOrders = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getAssignedOrders();
      if (response.success) {
        setOrders(response.data.assigned_orders || []);
      } else {
        setError('Impossible de charger les commandes');
      }
    } catch (err) {
      setError('Erreur lors du chargement des commandes');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = async (deliveryId) => {
    try {
      setActionLoading(prev => ({ ...prev, [deliveryId]: true }));
      const response = await acceptDelivery(deliveryId);
      if (response.success) {
        // Rafraîchir la liste
        fetchAssignedOrders();
      } else {
        alert(response.error || 'Erreur lors de l\'acceptation');
      }
    } catch (err) {
      alert('Erreur: ' + err.message);
    } finally {
      setActionLoading(prev => ({ ...prev, [deliveryId]: false }));
    }
  };

  const handleReject = async (deliveryId) => {
    if (!window.confirm('Êtes-vous sûr de vouloir refuser cette commande?')) return;
    
    try {
      setActionLoading(prev => ({ ...prev, [deliveryId]: true }));
      const response = await rejectDelivery(deliveryId);
      if (response.success) {
        // Rafraîchir la liste
        fetchAssignedOrders();
      } else {
        alert(response.error || 'Erreur lors du refus');
      }
    } catch (err) {
      alert('Erreur: ' + err.message);
    } finally {
      setActionLoading(prev => ({ ...prev, [deliveryId]: false }));
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      'assigned': 'bg-blue-100 text-blue-800',
      'pending': 'bg-yellow-100 text-yellow-800',
      'accepted': 'bg-green-100 text-green-800',
      'picked_up': 'bg-purple-100 text-purple-800',
      'in_transit': 'bg-indigo-100 text-indigo-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const filteredOrders = filterStatus === 'all' 
    ? orders 
    : orders.filter(o => {
        if (filterStatus === 'pending') return ['assigned', 'pending'].includes(o.status);
        if (filterStatus === 'in_progress') return ['accepted', 'picked_up', 'in_transit'].includes(o.status);
        return o.status === filterStatus;
      });

  if (loading) {
    return (
      <div className="flex justify-center items-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">
            Commandes assignées ({filteredOrders.length})
          </h3>
          <button
            onClick={fetchAssignedOrders}
            className="text-sm px-3 py-1 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 transition"
          >
            Actualiser
          </button>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="px-6 py-3 border-b border-gray-200 flex gap-2">
        <button
          onClick={() => setFilterStatus('all')}
          className={`px-3 py-1 rounded text-sm font-medium transition ${
            filterStatus === 'all'
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Toutes ({orders.length})
        </button>
        <button
          onClick={() => setFilterStatus('pending')}
          className={`px-3 py-1 rounded text-sm font-medium transition ${
            filterStatus === 'pending'
              ? 'bg-yellow-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          En attente ({orders.filter(o => ['assigned', 'pending'].includes(o.status)).length})
        </button>
        <button
          onClick={() => setFilterStatus('in_progress')}
          className={`px-3 py-1 rounded text-sm font-medium transition ${
            filterStatus === 'in_progress'
              ? 'bg-green-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          En cours ({orders.filter(o => ['accepted', 'picked_up', 'in_transit'].includes(o.status)).length})
        </button>
      </div>

      {error && (
        <div className="mx-6 my-4 p-3 bg-red-100 text-red-700 rounded">
          {error}
        </div>
      )}

      {/* Orders list */}
      <div className="divide-y divide-gray-200">
        {filteredOrders.length === 0 ? (
          <div className="px-6 py-8 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <p className="mt-2 text-gray-600">
              {filterStatus === 'all' 
                ? 'Aucune commande assignée'
                : `Aucune commande ${filterStatus === 'pending' ? 'en attente' : 'en cours'}`
              }
            </p>
          </div>
        ) : (
          filteredOrders.map((order) => (
            <div key={order.id} className="px-6 py-4 hover:bg-gray-50 transition">
              <div className="flex items-start justify-between gap-4">
                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="text-sm font-semibold text-gray-900">
                      Commande #{order.order_number}
                    </h4>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(order.status)}`}>
                      {order.status_display}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">
                    <strong>Magasin:</strong> {order.store_name}
                  </p>
                  <p className="text-sm text-gray-600 mb-2">
                    <strong>Client:</strong> {order.client_name} ({order.client_phone})
                  </p>
                  <div className="grid grid-cols-2 gap-2 text-sm text-gray-600 mt-2">
                    <div>
                      <strong>Adresse pickup:</strong>
                      <p className="text-xs">{order.pickup_address}</p>
                    </div>
                    <div>
                      <strong>Adresse livraison:</strong>
                      <p className="text-xs">{order.delivery_address}</p>
                    </div>
                  </div>
                  {order.estimated_duration && (
                    <p className="text-xs text-gray-500 mt-1">
                      Durée estimée: {order.estimated_duration} min
                    </p>
                  )}
                </div>

                {/* Right side - Amount & Actions */}
                <div className="flex flex-col items-end gap-3">
                  <div className="text-right">
                    <p className="text-lg font-bold text-gray-900">
                      {formatCurrency(order.total_amount)}
                    </p>
                    <p className="text-xs text-green-600 font-medium">
                      +{formatCurrency(order.fee)} frais
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {order.items_count} article(s)
                    </p>
                  </div>

                  {/* Actions */}
                  {['assigned', 'pending'].includes(order.status) && (
                    <div className="flex gap-2 w-full">
                      <button
                        onClick={() => handleAccept(order.id)}
                        disabled={actionLoading[order.id]}
                        className="flex-1 px-3 py-2 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition"
                      >
                        {actionLoading[order.id] ? 'Traitement...' : 'Accepter'}
                      </button>
                      <button
                        onClick={() => handleReject(order.id)}
                        disabled={actionLoading[order.id]}
                        className="flex-1 px-3 py-2 bg-red-600 text-white rounded text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition"
                      >
                        {actionLoading[order.id] ? 'Traitement...' : 'Refuser'}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default AssignedOrdersList;
