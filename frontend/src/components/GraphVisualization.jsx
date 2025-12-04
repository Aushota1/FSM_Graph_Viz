import React, { useCallback, useMemo } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  ReactFlowProvider,
} from 'reactflow'
import 'reactflow/dist/style.css'
import './GraphVisualization.css'

function GraphVisualizationInner({ graph }) {
  const states = graph.states || []
  const transitions = graph.transitions || []
  const resetState = graph.reset_state

  // Вычисляем позиции узлов по окружности
  const nodePositions = useMemo(() => {
    const positions = {}
    const centerX = 400
    const centerY = 300
    const radius = Math.min(250, 200 + states.length * 10)
    const n = states.length

    states.forEach((state, i) => {
      const angle = (2 * Math.PI * i) / n - Math.PI / 2
      positions[state] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      }
    })

    return positions
  }, [states])

  // Создаем узлы
  const initialNodes = useMemo(() => {
    return states.map((state) => {
      const pos = nodePositions[state]
      const isReset = resetState === state

      return {
        id: state,
        type: 'default',
        position: pos,
        data: { label: state },
        style: {
          background: isReset ? '#e8ffe8' : '#eef2ff',
          border: isReset ? '2.5px solid #006600' : '2px solid #333366',
          borderRadius: '50%',
          width: 60,
          height: 60,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '12px',
          fontWeight: isReset ? 'bold' : 'normal',
        },
      }
    })
  }, [states, nodePositions, resetState])

  // Создаем рёбра
  const initialEdges = useMemo(() => {
    return transitions.map((trans, index) => {
      const cond = trans.cond
      const hasCondition = cond && cond !== '1'

      return {
        id: `edge-${index}`,
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
          strokeWidth: 2,
          stroke: '#333',
        },
        labelStyle: {
          fill: '#000',
          fontWeight: 500,
          fontSize: '11px',
        },
        labelBgStyle: {
          fill: 'rgba(255, 255, 255, 0.8)',
          fillOpacity: 0.8,
        },
      }
    })
  }, [transitions])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  // Обновляем узлы и рёбра при изменении графа
  React.useEffect(() => {
    setNodes(initialNodes)
    setEdges(initialEdges)
  }, [initialNodes, initialEdges, setNodes, setEdges])

  return (
    <div className="graph-visualization">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        attributionPosition="bottom-left"
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  )
}

function GraphVisualization({ graph }) {
  return (
    <ReactFlowProvider>
      <GraphVisualizationInner graph={graph} />
    </ReactFlowProvider>
  )
}

export default GraphVisualization

