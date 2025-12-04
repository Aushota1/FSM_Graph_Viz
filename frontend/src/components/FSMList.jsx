import React from 'react'
import './FSMList.css'

function FSMList({ graphs, selectedGraphId, onSelectGraph }) {
  if (graphs.length === 0) {
    return (
      <div className="fsm-list">
        <div className="fsm-list-header">
          <h3>Список FSM</h3>
        </div>
        <div className="fsm-list-empty">
          <p>Нет найденных FSM</p>
          <p className="hint">Загрузите код и нажмите "Парсить"</p>
        </div>
      </div>
    )
  }

  return (
    <div className="fsm-list">
      <div className="fsm-list-header">
        <h3>Список FSM ({graphs.length})</h3>
      </div>
      <div className="fsm-list-items">
        {graphs.map((graph) => {
          const isSelected = graph.graph_id === selectedGraphId
          const scope = graph.scope || 'unknown'
          const enumName = graph.enum_name || '<anon enum>'
          const stateVar = graph.state_var || 'state'
          const numStates = graph.metadata?.num_states || graph.states?.length || 0
          const numTrans = graph.metadata?.num_transitions || graph.transitions?.length || 0

          return (
            <div
              key={graph.graph_id}
              className={`fsm-list-item ${isSelected ? 'selected' : ''}`}
            >
              <div 
                className="fsm-item-content"
                onClick={() => onSelectGraph(graph.graph_id)}
              >
                <div className="fsm-item-title">
                  {scope}
                </div>
                <div className="fsm-item-details">
                  <div className="fsm-item-detail">
                    <span className="label">Enum:</span> {enumName}
                  </div>
                  <div className="fsm-item-detail">
                    <span className="label">State:</span> {stateVar}
                  </div>
                  <div className="fsm-item-stats">
                    <span>{numStates} состояний</span>
                    <span>•</span>
                    <span>{numTrans} переходов</span>
                  </div>
                </div>
              </div>
              <button
                className="fsm-item-open-btn"
                onClick={(e) => {
                  e.stopPropagation()
                  onSelectGraph(graph.graph_id)
                }}
                title="Открыть граф"
              >
                →
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default FSMList

