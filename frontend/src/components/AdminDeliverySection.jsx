import { useState, useEffect } from 'react';
import { getDeliveryAgents, createDeliveryAgent, updateDeliveryAgent, toggleDeliveryAgentStatus } from '../services/adminService';

const AdminDeliverySection = () => {
  const [activeTab, setActiveTab] = useState('agents');
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showViewModal, setShowViewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [newAgent, setNewAgent] = useState({
    phone: '',
    first_name: '',
    last_name: '',
    email: '',
    city: 'Libreville',
    password: '',
    confirm_password: '',
    delivery_profile: {
      vehicle_type: 'Moto',
      vehicle_plate: '',
      cin_number: ''
    }
  });

  useEffect(() => {
    if (activeTab === 'agents') {
      loadAgents();
    }
  }, [activeTab]);

  const loadAgents = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDeliveryAgents();

      // Handle explicit backend error envelope
      if (data && data.success === false) {
        const msg = data.error?.message || 'Réponse API invalide pour la liste des livreurs.';
        throw new Error(msg);
      }

      // Normalize API response to an array (supports raw array, {data: [...]}, {results: [...]})
      const agentsArray = Array.isArray(data)
        ? data
        : Array.isArray(data?.data)
          ? data.data
          : Array.isArray(data?.results)
            ? data.results
            : [];

      if (!Array.isArray(agentsArray)) {
        throw new Error('Réponse API invalide pour la liste des livreurs.');
      }

      // Map API data to component format
      const formattedAgents = agentsArray.map(agent => {
        const fullName = `${agent.first_name || ''} ${agent.last_name || ''}`.trim();
        return {
          id: agent.id,
          name: fullName || 'Sans nom',
          first_name: agent.first_name || '',
          last_name: agent.last_name || '',
          phone: agent.phone,
          email: agent.email || '',
          city: agent.city || 'Libreville',
          total_deliveries: agent.profile?.total_deliveries || 0,
          daily_deliveries: agent.daily_deliveries || 0,
          rating: agent.profile?.average_rating || 0,
          status: agent.profile?.status || 'offline',
          is_active: agent.is_active,
          is_verified: agent.is_verified || false,
          is_available: agent.is_available || false,
          avatar: agent.profile_picture,
          vehicle_type: agent.profile?.vehicle_type || '',
          vehicle_plate: agent.profile?.vehicle_plate || '',
          cin_number: agent.profile?.cin_number || ''
        };
      });
      setAgents(formattedAgents);
    } catch (error) {
      console.error("Error loading delivery agents:", error);
      let errorMessage = "Impossible de charger les livreurs.";
      if (error.response) {
        if (error.response.status === 404) {
          errorMessage = "Erreur 404: Endpoint introuvable. Veuillez redémarrer le serveur Django.";
        } else if (error.response.status === 401) {
          errorMessage = "Session expirée ou non authentifié. Merci de vous reconnecter en tant qu'administrateur.";
        } else if (error.response.status === 403) {
          errorMessage = "Erreur 403: Accès refusé. Vous n'avez pas les droits administrateur.";
        } else if (error.response.status === 500) {
          errorMessage = "Erreur 500: Erreur interne du serveur.";
        } else {
          errorMessage = `Erreur ${error.response.status}: ${error.response.statusText}`;
        }
      } else if (error.request) {
        errorMessage = "Erreur réseau: Impossible de contacter le serveur. Vérifiez qu'il est démarré.";
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleViewAgent = (agent) => {
    setSelectedAgent(agent);
    setShowViewModal(true);
  };

  const handleEditAgent = (agent) => {
    setSelectedAgent(agent);
    setEditForm({
      first_name: agent.first_name,
      last_name: agent.last_name,
      email: agent.email,
      city: agent.city,
      delivery_profile: {
        vehicle_type: agent.vehicle_type,
        vehicle_plate: agent.vehicle_plate,
        cin_number: agent.cin_number
      }
    });
    setShowEditModal(true);
  };

  const handleUpdateAgent = async (e) => {
    e.preventDefault();
    try {
      await updateDeliveryAgent(selectedAgent.id, editForm);
      setShowEditModal(false);
      loadAgents();
      alert('Livreur mis à jour avec succès !');
    } catch (error) {
      console.error('Erreur lors de la mise à jour:', error);
      alert('Erreur lors de la mise à jour du livreur.');
    }
  };

  const handleToggleAgent = async (agent) => {
    const action = agent.is_active ? 'Désactiver' : 'Activer';
    if (window.confirm(`Êtes-vous sûr de vouloir ${action.toLowerCase()} ${agent.name} ?`)) {
      try {
        await toggleDeliveryAgentStatus(agent.id, agent.is_active);
        loadAgents();
        alert(`${agent.name} a été ${action.toLowerCase()} avec succès.`);
      } catch (error) {
        console.error('Erreur lors du changement de statut:', error);
        alert('Erreur lors du changement de statut.');
      }
    }
  };

  const handleAddAgent = async (e) => {
    e.preventDefault();
    
    if (newAgent.password !== newAgent.confirm_password) {
      alert("Les mots de passe ne correspondent pas.");
      return;
    }

    try {
      // Ensure delivery_profile is correctly structured for the backend
      const payload = {
        ...newAgent,
        delivery_profile: {
          vehicle_type: newAgent.delivery_profile.vehicle_type,
          vehicle_plate: newAgent.delivery_profile.vehicle_plate,
          cin_number: newAgent.delivery_profile.cin_number,
          status: 'offline' // Default status
        }
      };
      // Remove confirm_password from payload
      delete payload.confirm_password;
      
      await createDeliveryAgent(payload);
      setShowAddModal(false);
      setNewAgent({
        phone: '',
        first_name: '',
        last_name: '',
        email: '',
        city: 'Libreville',
        password: '',
        confirm_password: '',
        delivery_profile: {
          vehicle_type: 'Moto',
          vehicle_plate: '',
          cin_number: ''
        }
      });
      loadAgents();
      alert('Livreur ajouté avec succès !');
    } catch (error) {
      console.error("Error creating agent:", error);
      let errorMsg = 'Erreur lors de la création du livreur.';
      if (error.response && error.response.data) {
         errorMsg += ' ' + JSON.stringify(error.response.data);
      }
      alert(errorMsg);
    }
  };


  const getStatusBadge = (status) => {
    switch (status) {
      case 'available': return <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">Disponible</span>;
      case 'busy': return <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded-full text-xs">Occupé</span>;
      case 'offline': return <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded-full text-xs">Hors-ligne</span>;
      case 'suspended': return <span className="px-2 py-1 bg-red-100 text-red-800 rounded-full text-xs">Suspendu</span>;
      default: return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Tabs Navigation */}
      <div className="flex space-x-4 border-b border-gray-200 pb-2 overflow-x-auto">
        {['agents', 'attribution', 'active_orders', 'settings', 'stats', 'incidents'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium whitespace-nowrap ${
              activeTab === tab
                ? 'text-indigo-600 border-b-2 border-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab === 'agents' && 'Livreurs'}
            {tab === 'attribution' && 'Attribution'}
            {tab === 'active_orders' && 'Commandes en cours'}
            {tab === 'settings' && 'Paramètres'}
            {tab === 'stats' && 'Statistiques'}
            {tab === 'incidents' && 'Incidents'}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'agents' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">Liste des Livreurs</h2>
            <div className="flex gap-2">
              <button 
                onClick={() => setShowAddModal(true)}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm hover:bg-indigo-700"
              >
                ➕ Ajouter un livreur
              </button>
              <button 
                onClick={() => alert('Fonctionnalité Carte à venir')}
                className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md text-sm hover:bg-gray-50"
              >
                📍 Carte
              </button>
              <button 
                onClick={() => alert('Export non disponible')}
                className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md text-sm hover:bg-gray-50"
              >
                🧾 Exporter
              </button>
            </div>
          </div>

          <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
            {error && (
              <div className="p-4 bg-red-50 text-red-700 border-b border-red-100">
                {error}
              </div>
            )}
            {loading ? (
              <div className="p-8 text-center text-gray-500">Chargement des livreurs...</div>
            ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Livreur</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ville</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Total Liv.</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Auj.</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Note</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Statut</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {agents.map((agent) => (
                  <tr key={agent.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 font-bold">
                          {agent.name.substring(0, 2).toUpperCase()}
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">{agent.name}</div>
                          <div className="text-sm text-gray-500">{agent.phone}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{agent.city}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-center">{agent.total_deliveries}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-center">{agent.daily_deliveries}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-yellow-500 text-center font-bold">
                      {agent.rating} ⭐
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      {getStatusBadge(agent.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button onClick={() => handleViewAgent(agent)} className="text-indigo-600 hover:text-indigo-900 mr-3">
                        👁️ Voir
                      </button>
                      <button onClick={() => handleEditAgent(agent)} className="text-blue-600 hover:text-blue-900 mr-3">
                        ✏️ Modifier
                      </button>
                      <button onClick={() => handleToggleAgent(agent)} className="text-red-600 hover:text-red-900">
                        {agent.is_active ? '🚫 Désactiver' : '✅ Activer'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            )}
          </div>
        </div>
      )}
      
      {activeTab !== 'agents' && (
        <div className="p-8 text-center text-gray-500 bg-gray-50 rounded-lg border border-dashed border-gray-300">
          Section "{activeTab}" en cours de développement...
        </div>
      )}

      {/* Add Agent Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-bold mb-4">Ajouter un nouveau livreur</h3>
            <form onSubmit={handleAddAgent} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Prénom</label>
                  <input
                    type="text"
                    required
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                    value={newAgent.first_name}
                    onChange={(e) => setNewAgent({...newAgent, first_name: e.target.value})}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Nom</label>
                  <input
                    type="text"
                    required
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                    value={newAgent.last_name}
                    onChange={(e) => setNewAgent({...newAgent, last_name: e.target.value})}
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Téléphone</label>
                <input
                  type="text"
                  required
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                  value={newAgent.phone}
                  onChange={(e) => setNewAgent({...newAgent, phone: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  type="email"
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                  value={newAgent.email}
                  onChange={(e) => setNewAgent({...newAgent, email: e.target.value})}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Mot de passe</label>
                  <input
                    type="password"
                    required
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                    value={newAgent.password}
                    onChange={(e) => setNewAgent({...newAgent, password: e.target.value})}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Confirmer mot de passe</label>
                  <input
                    type="password"
                    required
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                    value={newAgent.confirm_password}
                    onChange={(e) => setNewAgent({...newAgent, confirm_password: e.target.value})}
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Ville</label>
                <select
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                  value={newAgent.city}
                  onChange={(e) => setNewAgent({...newAgent, city: e.target.value})}
                >
                  <option value="Libreville">Libreville</option>
                  <option value="Port-Gentil">Port-Gentil</option>
                  <option value="Franceville">Franceville</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Véhicule</label>
                  <select
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                    value={newAgent.delivery_profile.vehicle_type}
                    onChange={(e) => setNewAgent({
                      ...newAgent, 
                      delivery_profile: {...newAgent.delivery_profile, vehicle_type: e.target.value}
                    })}
                  >
                    <option value="Moto">Moto</option>
                    <option value="Voiture">Voiture</option>
                    <option value="Vélo">Vélo</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Plaque / ID</label>
                  <input
                    type="text"
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                    value={newAgent.delivery_profile.vehicle_plate}
                    onChange={(e) => setNewAgent({
                      ...newAgent, 
                      delivery_profile: {...newAgent.delivery_profile, vehicle_plate: e.target.value}
                    })}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                >
                  Créer Livreur
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Agent Modal */}
      {showViewModal && selectedAgent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">Détails du livreur</h3>
              <button onClick={() => setShowViewModal(false)} className="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <div className="space-y-3">
              <div className="flex items-center">
                <div className="h-16 w-16 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-xl mr-4">
                  {selectedAgent.name.substring(0, 2).toUpperCase()}
                </div>
                <div>
                  <div className="text-xl font-semibold">{selectedAgent.name}</div>
                  <div className="text-sm text-gray-500">{selectedAgent.phone}</div>
                </div>
              </div>
              <hr />
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="font-medium">Email:</span> {selectedAgent.email || 'Non renseigné'}</div>
                <div><span className="font-medium">Ville:</span> {selectedAgent.city}</div>
                <div><span className="font-medium">Véhicule:</span> {selectedAgent.vehicle_type || 'Non renseigné'}</div>
                <div><span className="font-medium">Plaque:</span> {selectedAgent.vehicle_plate || 'Non renseigné'}</div>
                <div><span className="font-medium">CIN:</span> {selectedAgent.cin_number || 'Non renseigné'}</div>
                <div><span className="font-medium">Statut:</span> {getStatusBadge(selectedAgent.status)}</div>
                <div><span className="font-medium">Total Livraisons:</span> {selectedAgent.total_deliveries}</div>
                <div><span className="font-medium">Aujourd'hui:</span> {selectedAgent.daily_deliveries}</div>
                <div><span className="font-medium">Note:</span> {selectedAgent.rating} ⭐</div>
                <div><span className="font-medium">Actif:</span> {selectedAgent.is_active ? '✅ Oui' : '❌ Non'}</div>
                <div><span className="font-medium">Vérifié:</span> {selectedAgent.is_verified ? '✅ Oui' : '❌ Non'}</div>
                <div><span className="font-medium">Disponible:</span> {selectedAgent.is_available ? '✅ Oui' : '❌ Non'}</div>
              </div>
            </div>
            <div className="flex justify-end mt-6">
              <button
                onClick={() => setShowViewModal(false)}
                className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Agent Modal */}
      {showEditModal && selectedAgent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">Modifier le livreur</h3>
              <button onClick={() => setShowEditModal(false)} className="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <form onSubmit={handleUpdateAgent} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Prénom</label>
                  <input type="text" value={editForm.first_name} onChange={(e) => setEditForm({...editForm, first_name: e.target.value})} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Nom</label>
                  <input type="text" value={editForm.last_name} onChange={(e) => setEditForm({...editForm, last_name: e.target.value})} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Téléphone</label>
                <input type="text" value={selectedAgent.phone} disabled className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2 bg-gray-100" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input type="email" value={editForm.email} onChange={(e) => setEditForm({...editForm, email: e.target.value})} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Ville</label>
                <select value={editForm.city} onChange={(e) => setEditForm({...editForm, city: e.target.value})} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2">
                  <option value="Libreville">Libreville</option>
                  <option value="Port-Gentil">Port-Gentil</option>
                  <option value="Franceville">Franceville</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Véhicule</label>
                  <select value={editForm.delivery_profile.vehicle_type} onChange={(e) => setEditForm({...editForm, delivery_profile: {...editForm.delivery_profile, vehicle_type: e.target.value}})} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2">
                    <option value="Moto">Moto</option>
                    <option value="Voiture">Voiture</option>
                    <option value="Vélo">Vélo</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Plaque / ID</label>
                  <input type="text" value={editForm.delivery_profile.vehicle_plate} onChange={(e) => setEditForm({...editForm, delivery_profile: {...editForm.delivery_profile, vehicle_plate: e.target.value}})} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">CIN</label>
                <input type="text" value={editForm.delivery_profile.cin_number} onChange={(e) => setEditForm({...editForm, delivery_profile: {...editForm.delivery_profile, cin_number: e.target.value}})} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2" />
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <button type="button" onClick={() => setShowEditModal(false)} className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
                  Annuler
                </button>
                <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
                  Enregistrer
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDeliverySection;