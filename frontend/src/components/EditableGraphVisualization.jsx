import React, { useCallback, useMemo, useState, useRef } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Panel,
  ReactFlowProvider,
} from 'reactflow'
import 'reactflow/dist/style.css'
import './EditableGraphVisualization.css'

// Force-directed layout algorithm
function calculateForceDirectedLayout(states, transitions, width, height, iterations = 100) {
  const positions = {}
  const k = Math.sqrt((width * height) / Math.max(states.length, 1))
  
  // Initialize positions in a circle
  states.forEach((state, i) => {
    const angle = (2 * Math.PI * i) / states.length - Math.PI / 2
    positions[state] = {
      x: width / 2 + (width * 0.3) * Math.cos(angle),
      y: height / 2 + (height * 0.3) * Math.sin(angle),
    }
  })
  
  let temperature = 1.0
  const coolingRate = temperature / iterations
  
  for (let iter = 0; iter < iterations; iter++) {
    const forces = {}
    states.forEach(state => {
      forces[state] = { x: 0, y: 0 }
    })
    
    // Repulsion forces between all nodes
    for (let i = 0; i < states.length; i++) {
      for (let j = i + 1; j < states.length; j++) {
        const state1 = states[i]
        const state2 = states[j]
        const dx = positions[state2].x - positions[state1].x
        const dy = positions[state2].y - positions[state1].y
        const dist = Math.hypot(dx, dy) || 0.1
        
        const force = (k * k) / dist
        const fx = (force * dx) / dist
        const fy = (force * dy) / dist
        
        forces[state1].x -= fx
        forces[state1].y -= fy
        forces[state2].x += fx
        forces[state2].y += fy
      }
    }
    
    // Attraction forces along edges
    transitions.forEach(trans => {
      const fromState = trans.from
      const toState = trans.to
      if (positions[fromState] && positions[toState]) {
        const dx = positions[toState].x - positions[fromState].x
        const dy = positions[toState].y - positions[fromState].y
        const dist = Math.hypot(dx, dy) || 0.1
        
        const force = (dist * dist) / k
        const fx = (force * dx) / dist
        const fy = (force * dy) / dist
        
        forces[fromState].x += fx
        forces[fromState].y += fy
        forces[toState].x -= fx
        forces[toState].y -= fy
      }
    })
    
    // Apply forces
    states.forEach(state => {
      const force = forces[state]
      const forceMag = Math.hypot(force.x, force.y)
      
      if (forceMag > 0) {
        const maxForce = 10.0
        const scale = forceMag > maxForce ? maxForce / forceMag : 1
        const fx = force.x * scale * temperature * 0.1
        const fy = force.y * scale * temperature * 0.1
        
        positions[state].x = Math.max(50, Math.min(width - 50, positions[state].x + fx))
        positions[state].y = Math.max(50, Math.min(height - 50, positions[state].y + fy))
      }
    })
    
    temperature -= coolingRate
  }
  
  return positions
}

function EditableGraphVisualizationInner({ graph, onGraphChange, readOnly = false }) {
  const states = graph.states || []
  const transitions = graph.transitions || []
  const resetState = graph.reset_state
  const [selectedNode, setSelectedNode] = useState(null)
  const [selectedEdge, setSelectedEdge] = useState(null)
  const [isAddingState, setIsAddingState] = useState(false)
  const [newStateName, setNewStateName] = useState('')
  const [isConnecting, setIsConnecting] = useState(false)
  const [connectionStart, setConnectionStart] = useState(null)
  const reactFlowWrapper = useRef(null)

  // Calculate initial positions using force-directed layout
  const nodePositions = useMemo(() => {
    if (states.length === 0) return {}
    const width = 800
    const height = 600
    return calculateForceDirectedLayout(states, transitions, width, height)
  }, [states, transitions])

  // Create nodes
  const initialNodes = useMemo(() => {
    return states.map((state) => {
      const pos = nodePositions[state] || { x: 400, y: 300 }
      const isReset = resetState === state
      const isSelected = selectedNode === state

      return {
        id: state,
        type: 'default',
        position: pos,
        data: { 
          label: state,
          isReset,
        },
        style: {
          background: isSelected 
            ? '#ffd700' 
            : isReset 
              ? '#e8ffe8' 
              : '#eef2ff',
          border: isSelected
            ? '3px solid #ff8c00'
            : isReset
              ? '2.5px solid #006600'
              : '2px solid #333366',
          borderRadius: '50%',
          width: 70,
          height: 70,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '12px',
          fontWeight: isReset || isSelected ? 'bold' : 'normal',
          boxShadow: isSelected ? '0 0 10px rgba(255, 140, 0, 0.5)' : 'none',
        },
      }
    })
  }, [states, nodePositions, resetState, selectedNode])

  // Create edges
  const initialEdges = useMemo(() => {
    return transitions.map((trans, index) => {
      const cond = trans.cond
      const hasCondition = cond && cond !== '1' && cond !== ''
      const edgeId = `edge-${trans.from}-${trans.to}-${index}`
      const isSelected = selectedEdge === edgeId

      return {
        id: edgeId,
        source: trans.from,
        target: trans.to,
        label: hasCondition ? cond : '',
        type: 'smoothstep',
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 20,
          height: 20,
        },
        style: {
          strokeWidth: isSelected ? 3 : 2,
          stroke: isSelected ? '#ff8c00' : '#333',
        },
        labelStyle: {
          fill: '#000',
          fontWeight: 500,
          fontSize: '11px',
        },
        labelBgStyle: {
          fill: 'rgba(255, 255, 255, 0.9)',
          fillOpacity: 0.9,
        },
        data: {
          condition: cond || '1',
          originalIndex: index,
        },
      }
    })
  }, [transitions, selectedEdge])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  // Handle adding transition
  const handleAddTransition = useCallback((from, to) => {
    if (readOnly) return
    
    const condition = prompt('Введите условие перехода (или оставьте пустым для безусловного):', '1')
    if (condition === null) return // User cancelled
    
    const newTransitions = [...transitions, {
      from,
      to,
      cond: condition.trim() || '1',
    }]
    
    onGraphChange({
      ...graph,
      transitions: newTransitions,
      metadata: {
        ...graph.metadata,
        num_transitions: newTransitions.length,
      },
    })
  }, [graph, transitions, onGraphChange, readOnly])

  // Update nodes and edges when graph changes
  React.useEffect(() => {
    setNodes(initialNodes)
    setEdges(initialEdges)
  }, [initialNodes, initialEdges, setNodes, setEdges])

  // Handle node click
  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node.id)
    setSelectedEdge(null)
    if (isConnecting && connectionStart) {
      // Complete connection
      handleAddTransition(connectionStart, node.id)
      setIsConnecting(false)
      setConnectionStart(null)
    }
  }, [isConnecting, connectionStart, handleAddTransition])

  // Handle edge click
  const onEdgeClick = useCallback((event, edge) => {
    setSelectedEdge(edge.id)
    setSelectedNode(null)
  }, [])

  // Handle pane click
  const onPaneClick = useCallback(() => {
    setSelectedNode(null)
    setSelectedEdge(null)
  }, [])

  // Handle connection start
  const onConnectStart = useCallback((event, { nodeId }) => {
    if (!readOnly) {
      setIsConnecting(true)
      setConnectionStart(nodeId)
    }
  }, [readOnly])

  // Handle connection end
  const onConnectEnd = useCallback((event) => {
    if (!readOnly && isConnecting && connectionStart) {
      const targetNode = event.target.closest('.react-flow__node')
      if (targetNode) {
        const targetId = targetNode.getAttribute('data-id')
        if (targetId && targetId !== connectionStart) {
          handleAddTransition(connectionStart, targetId)
        }
      }
      setIsConnecting(false)
      setConnectionStart(null)
    }
  }, [isConnecting, connectionStart, readOnly, handleAddTransition])

  // Handle deleting selected element
  const handleDelete = useCallback(() => {
    if (readOnly) return
    
    if (selectedNode) {
      // Delete state and all related transitions
      const newStates = states.filter(s => s !== selectedNode)
      const newTransitions = transitions.filter(
        t => t.from !== selectedNode && t.to !== selectedNode
      )
      
      let newResetState = resetState
      if (resetState === selectedNode) {
        newResetState = null
      }
      
      onGraphChange({
        ...graph,
        states: newStates,
        transitions: newTransitions,
        reset_state: newResetState,
        metadata: {
          num_states: newStates.length,
          num_transitions: newTransitions.length,
        },
      })
      
      setSelectedNode(null)
    } else if (selectedEdge) {
      // Delete transition
      const edge = edges.find(e => e.id === selectedEdge)
      if (edge) {
        const newTransitions = transitions.filter((t, idx) => {
          return edge.data.originalIndex !== idx
        })
        
        onGraphChange({
          ...graph,
          transitions: newTransitions,
          metadata: {
            ...graph.metadata,
            num_transitions: newTransitions.length,
          },
        })
        
        setSelectedEdge(null)
      }
    }
  }, [selectedNode, selectedEdge, states, transitions, resetState, graph, edges, onGraphChange, readOnly])

  // Handle keyboard shortcuts
  React.useEffect(() => {
    const handleKeyDown = (event) => {
      if (readOnly) return
      
      if (event.key === 'Delete' || event.key === 'Backspace') {
        if (selectedNode || selectedEdge) {
          event.preventDefault()
          handleDelete()
        }
      }
    }
    
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedNode, selectedEdge, handleDelete, readOnly])

  // Handle adding new state
  const handleAddState = useCallback(() => {
    if (readOnly || !isAddingState) return
    
    const name = newStateName.trim()
    if (name && !states.includes(name)) {
      const newStates = [...states, name]
      onGraphChange({
        ...graph,
        states: newStates,
        metadata: {
          ...graph.metadata,
          num_states: newStates.length,
        },
      })
      setNewStateName('')
      setIsAddingState(false)
    } else if (name) {
      alert('Состояние с таким именем уже существует')
    }
  }, [isAddingState, newStateName, states, graph, onGraphChange, readOnly])

  // Handle setting reset state
  const handleSetResetState = useCallback(() => {
    if (readOnly || !selectedNode) return
    
    onGraphChange({
      ...graph,
      reset_state: selectedNode,
    })
  }, [selectedNode, graph, onGraphChange, readOnly])

  // Handle editing edge condition
  const handleEditEdgeCondition = useCallback(() => {
    if (readOnly || !selectedEdge) return
    
    const edge = edges.find(e => e.id === selectedEdge)
    if (edge) {
      const currentCond = edge.data.condition || '1'
      const newCond = prompt('Введите новое условие перехода:', currentCond)
      if (newCond !== null) {
        const newTransitions = transitions.map((t, idx) => {
          if (idx === edge.data.originalIndex) {
            return { ...t, cond: newCond.trim() || '1' }
          }
          return t
        })
        
        onGraphChange({
          ...graph,
          transitions: newTransitions,
        })
      }
    }
  }, [selectedEdge, edges, transitions, graph, onGraphChange, readOnly])

  return (
    <div className="editable-graph-visualization" ref={reactFlowWrapper}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        onConnectStart={readOnly ? undefined : onConnectStart}
        onConnectEnd={readOnly ? undefined : onConnectEnd}
        fitView
        attributionPosition="bottom-left"
        connectionLineStyle={{ stroke: '#ff8c00', strokeWidth: 2 }}
      >
        <Background />
        <Controls />
        <MiniMap />
        
        {!readOnly && (
          <Panel position="top-left" className="graph-controls-panel">
            <div className="graph-controls">
              <button
                onClick={() => setIsAddingState(true)}
                className="control-btn"
                title="Добавить состояние"
              >
                + Состояние
              </button>
              {selectedNode && (
                <>
                  <button
                    onClick={handleSetResetState}
                    className="control-btn"
                    title="Установить как reset-состояние"
                  >
                    ⚡ Reset
                  </button>
                  <button
                    onClick={() => {
                      setIsConnecting(true)
                      setConnectionStart(selectedNode)
                    }}
                    className="control-btn"
                    title="Добавить переход"
                  >
                    ➡ Переход
                  </button>
                </>
              )}
              {selectedEdge && (
                <button
                  onClick={handleEditEdgeCondition}
                  className="control-btn"
                  title="Редактировать условие"
                >
                  ✏ Условие
                </button>
              )}
              {(selectedNode || selectedEdge) && (
                <button
                  onClick={handleDelete}
                  className="control-btn delete-btn"
                  title="Удалить (Delete)"
                >
                  🗑 Удалить
                </button>
              )}
            </div>
          </Panel>
        )}
        
        {isAddingState && (
          <Panel position="top-center" className="add-state-panel">
            <div className="add-state-form">
              <input
                type="text"
                value={newStateName}
                onChange={(e) => setNewStateName(e.target.value)}
                placeholder="Имя состояния"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleAddState()
                  } else if (e.key === 'Escape') {
                    setIsAddingState(false)
                    setNewStateName('')
                  }
                }}
                autoFocus
              />
              <button onClick={handleAddState}>Добавить</button>
              <button onClick={() => {
                setIsAddingState(false)
                setNewStateName('')
              }}>Отмена</button>
            </div>
          </Panel>
        )}
      </ReactFlow>
    </div>
  )
}

function EditableGraphVisualization({ graph, onGraphChange, readOnly = false }) {
  return (
    <ReactFlowProvider>
      <EditableGraphVisualizationInner
        graph={graph}
        onGraphChange={onGraphChange}
        readOnly={readOnly}
      />
    </ReactFlowProvider>
  )
}

export default EditableGraphVisualization

