import React, { useEffect, useState } from 'react'

export default function SubscriptionPlans() {
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const resp = await fetch('/api/v1/dashboard/subscription/plans/', { credentials: 'include' })
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
        const data = await resp.json()
        if (data.success) setPlans(data.plans || [])
        else setError(data.error || 'Erreur serveur')
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handlePurchase = async (plan) => {
    try {
      const resp = await fetch('/api/v1/dashboard/subscription/purchase/', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_id: plan.id })
      })
      const data = await resp.json()
      if (data.success) alert(`Payment intent created. Redirect to: ${data.payment_intent.payment_url}`)
      else alert(`Erreur: ${data.error}`)
    } catch (e) {
      alert(e.message)
    }
  }

  if (loading) return <div className="p-6">Chargement des plans...</div>
  if (error) return <div className="p-6 text-red-600">Erreur: {error}</div>

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Forfaits d'abonnement</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {plans.map(plan => (
          <div key={plan.id} className="border rounded p-4 shadow-sm">
            <h2 className="text-xl font-semibold">{plan.name} — {plan.price} FCFA/mois</h2>
            <p className="text-sm text-gray-600 my-2">{plan.description}</p>
            <ul className="text-sm mb-3">
              {plan.feature_list && plan.feature_list.map((f, i) => <li key={i}>• {f}</li>)}
            </ul>
            <button
              className="bg-blue-600 text-white px-3 py-1 rounded"
              onClick={() => handlePurchase(plan)}
            >
              Acheter / Prévisualiser
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
