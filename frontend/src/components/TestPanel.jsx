import React, { useState } from 'react';
import './TestPanel.css';

/**
 * TestPanel Component
 * Allows testing Phase 1 validation directly from the UI
 */
export function TestPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [testLog, setTestLog] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState(null);

  const addLog = (message, type = 'info') => {
    setTestLog(prev => [...prev, { message, type, time: new Date().toLocaleTimeString() }]);
  };

  const clearLog = () => {
    setTestLog([]);
    setResults(null);
  };

  const runTests = async () => {
    setIsRunning(true);
    clearLog();
    addLog('🔍 Démarrage des tests Phase 1...', 'info');

    try {
      // Import test function
      const { runPhase1Tests } = await import('../utils/testPhase1Validation');
      
      addLog('📝 Exécution de la suite de tests...', 'info');
      const testResults = await runPhase1Tests();
      
      addLog(`✓ Tests terminés: ${testResults.passed} réussis, ${testResults.failed} échoués`, 
        testResults.failed === 0 ? 'success' : 'warning');
      
      setResults(testResults);
      
    } catch (error) {
      addLog(`✗ Erreur: ${error.message}`, 'error');
    } finally {
      setIsRunning(false);
    }
  };

  const togglePanel = () => {
    setIsOpen(!isOpen);
  };

  return (
    <>
      {/* Floating Button */}
      <div className="test-panel-button">
        <button 
          onClick={togglePanel}
          className="test-toggle-btn"
          title="Ouvrir/Fermer le panel de test"
        >
          🧪
        </button>
      </div>

      {/* Test Panel */}
      {isOpen && (
        <div className="test-panel">
          <div className="test-panel-header">
            <h3>🧪 Test Phase 1 - Status Validation</h3>
            <button className="close-btn" onClick={togglePanel}>✕</button>
          </div>

          <div className="test-panel-content">
            {/* Controls */}
            <div className="test-controls">
              <button 
                onClick={runTests}
                disabled={isRunning}
                className="run-tests-btn"
              >
                {isRunning ? '⏳ Exécution...' : '▶️ Exécuter les tests'}
              </button>
              <button 
                onClick={clearLog}
                disabled={isRunning || testLog.length === 0}
                className="clear-log-btn"
              >
                🗑️ Effacer
              </button>
            </div>

            {/* Test Log */}
            <div className="test-log">
              <div className="log-header">Résultats:</div>
              {testLog.length === 0 ? (
                <div className="log-empty">
                  Cliquez sur "Exécuter les tests" pour démarrer la suite de tests Phase 1
                </div>
              ) : (
                <div className="log-entries">
                  {testLog.map((entry, idx) => (
                    <div key={idx} className={`log-entry log-${entry.type}`}>
                      <span className="log-time">[{entry.time}]</span>
                      <span className="log-message">{entry.message}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Results Summary */}
            {results && (
              <div className="test-results">
                <div className="results-header">📊 Résumé des tests:</div>
                <div className="results-stats">
                  <div className="stat passed">
                    <span className="stat-label">✓ Réussis:</span>
                    <span className="stat-value">{results.passed}</span>
                  </div>
                  <div className="stat failed">
                    <span className="stat-label">✗ Échoués:</span>
                    <span className="stat-value">{results.failed}</span>
                  </div>
                  <div className="stat total">
                    <span className="stat-label">Total:</span>
                    <span className="stat-value">{results.passed + results.failed}</span>
                  </div>
                </div>

                {/* Details */}
                {results.details.length > 0 && (
                  <div className="results-details">
                    {results.details.map((detail, idx) => (
                      <div key={idx} className={`detail-item ${detail.passed ? 'success' : 'error'}`}>
                        <span className="detail-icon">
                          {detail.passed ? '✓' : '✗'}
                        </span>
                        <div className="detail-info">
                          <div className="detail-name">{detail.name}</div>
                          <div className="detail-description">{detail.details}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Info Section */}
            <div className="test-info">
              <details>
                <summary>📖 À propos de ces tests</summary>
                <div className="info-content">
                  <p>Cette suite de tests valide l'implémentation de Phase 1:</p>
                  <ul>
                    <li><strong>Validation des statuts:</strong> Vérifie que seules les transitions valides sont autorisées</li>
                    <li><strong>Contrôle d'accès:</strong> Teste les permissions basées sur les rôles</li>
                    <li><strong>Audit logging:</strong> Confirme que les actions sont enregistrées</li>
                    <li><strong>Détection de fraude:</strong> Teste la détection des accès non autorisés</li>
                  </ul>
                  <p><strong>Tests inclus:</strong></p>
                  <ol>
                    <li>Authentification du livreur</li>
                    <li>Récupération des livraisons assignées</li>
                    <li>Acceptation valide d'une livraison</li>
                    <li>Rejet des transitions invalides</li>
                    <li>Démarrage de la livraison</li>
                    <li>Confirmation de la livraison</li>
                    <li>Vérification des logs d'audit</li>
                  </ol>
                </div>
              </details>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default TestPanel;
