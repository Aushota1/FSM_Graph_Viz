import React, { useState } from 'react'
import './DetailsPanel.css'

function DetailsPanel({ graph }) {
  const [activeTab, setActiveTab] = useState('details')

  if (!graph) return null

  const scope = graph.scope || ''
  const enumName = graph.enum_name || '(anonymous)'
  const stateVar = graph.state_var || 'state'
  const nextStateVar = graph.next_state_var || '(none)'
  const resetState = graph.reset_state || '(unknown)'
  const states = graph.states || []
  const transitions = graph.transitions || []
  const metadata = graph.metadata || {}
  const numStates = metadata.num_states || states.length
  const numTrans = metadata.num_transitions || transitions.length

  const normalizeCond = (cond) => {
    if (!cond || cond === '1') return ''
    return cond.trim()
  }

  return (
    <div className="details-panel">
      <div className="details-tabs">
        <button
          className={`tab ${activeTab === 'details' ? 'active' : ''}`}
          onClick={() => setActiveTab('details')}
        >
          Детали
        </button>
        <button
          className={`tab ${activeTab === 'transitions' ? 'active' : ''}`}
          onClick={() => setActiveTab('transitions')}
        >
          Переходы ({numTrans})
        </button>
      </div>

      <div className="details-content">
        {activeTab === 'details' && (
          <div className="details-info">
            <div className="info-section">
              <h4>Основная информация</h4>
              <div className="info-row">
                <span className="info-label">Scope:</span>
                <span className="info-value">{scope}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Enum type:</span>
                <span className="info-value">{enumName}</span>
              </div>
              <div className="info-row">
                <span className="info-label">State variable:</span>
                <span className="info-value">{stateVar}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Next state variable:</span>
                <span className="info-value">{nextStateVar}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Reset state:</span>
                <span className="info-value">{resetState}</span>
              </div>
            </div>

            <div className="info-section">
              <h4>Статистика</h4>
              <div className="info-row">
                <span className="info-label">Состояний:</span>
                <span className="info-value">{numStates}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Переходов:</span>
                <span className="info-value">{numTrans}</span>
              </div>
            </div>

            <div className="info-section">
              <h4>Состояния ({states.length})</h4>
              <div className="states-list">
                {states.map((state, idx) => (
                  <div key={idx} className="state-item">
                    {state}
                    {state === resetState && (
                      <span className="reset-badge">reset</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'transitions' && (
          <div className="transitions-table">
            <table>
              <thead>
                <tr>
                  <th>From</th>
                  <th>To</th>
                  <th>Condition</th>
                </tr>
              </thead>
              <tbody>
                {transitions.length === 0 ? (
                  <tr>
                    <td colSpan="3" className="empty-cell">
                      Нет переходов
                    </td>
                  </tr>
                ) : (
                  transitions.map((trans, idx) => {
                    const cond = normalizeCond(trans.cond)
                    return (
                      <tr key={idx}>
                        <td>{trans.from}</td>
                        <td>{trans.to}</td>
                        <td className="condition-cell">
                          {cond || <span className="no-condition">—</span>}
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default DetailsPanel

