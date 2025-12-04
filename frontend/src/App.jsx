import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import CodeEditor from './components/CodeEditor'
import FSMList from './components/FSMList'
import GraphVisualization from './components/GraphVisualization'
import EditableGraphVisualization from './components/EditableGraphVisualization'
import DetailsPanel from './components/DetailsPanel'
import './App.css'

// Главная страница с редактором и списком
function MainPage({ code, setCode, graphs, setGraphs, selectedGraphId, setSelectedGraphId, loading, setLoading, error, setError }) {
  const navigate = useNavigate()

  const handleParse = async (codeToParse) => {
    setLoading(true)
    setError(null)
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/parse`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code: codeToParse,
          filename: 'source.sv'
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Ошибка парсинга')
      }

      const data = await response.json()
      setGraphs(data.graphs || [])
      if (data.graphs && data.graphs.length > 0) {
        setSelectedGraphId(data.graphs[0].graph_id)
      }
    } catch (err) {
      setError(err.message)
      console.error('Parse error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectGraph = (graphId) => {
    setSelectedGraphId(graphId)
    navigate(`/graph/${graphId}`)
  }

  return (
    <div className="main-page">
      <PanelGroup direction="vertical">
        <Panel defaultSize={50} minSize={30}>
          <CodeEditor
            code={code}
            onCodeChange={setCode}
            onParse={handleParse}
            loading={loading}
          />
          {error && (
            <div className="error-message">
              <strong>Ошибка:</strong> {error}
            </div>
          )}
        </Panel>
        <PanelResizeHandle className="resize-handle-horizontal" />
        <Panel defaultSize={50} minSize={30}>
          <FSMList
            graphs={graphs}
            selectedGraphId={selectedGraphId}
            onSelectGraph={handleSelectGraph}
          />
        </Panel>
      </PanelGroup>
    </div>
  )
}

// Страница визуализации графа
function GraphPage({ graphs, setGraphs, selectedGraphId, setSelectedGraphId }) {
  const { graphId } = useParams()
  const navigate = useNavigate()
  const [isEditing, setIsEditing] = useState(false)
  const [generatedCode, setGeneratedCode] = useState(null)
  const [showCodeModal, setShowCodeModal] = useState(false)
  
  // Если graphId из URL отличается от selectedGraphId, обновляем
  useEffect(() => {
    if (graphId && graphId !== selectedGraphId) {
      setSelectedGraphId(graphId)
    }
  }, [graphId, selectedGraphId, setSelectedGraphId])

  const selectedGraph = graphs.find(g => g.graph_id === graphId) || null
  const [localGraph, setLocalGraph] = useState(selectedGraph)

  // Обновляем localGraph при изменении selectedGraph
  useEffect(() => {
    if (selectedGraph) {
      setLocalGraph(selectedGraph)
    }
  }, [selectedGraph])

  const handleGraphChange = async (updatedGraph) => {
    setLocalGraph(updatedGraph)
    
    // Обновляем граф на сервере
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const response = await fetch(
        `${apiUrl}/api/graph/${graphId}/update`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ graph: updatedGraph }),
        }
      )
      
      if (response.ok) {
        // Обновляем локальный список графов
        setGraphs(prevGraphs => 
          prevGraphs.map(g => 
            g.graph_id === graphId ? updatedGraph : g
          )
        )
      }
    } catch (err) {
      console.error('Update error:', err)
      alert('Ошибка обновления графа: ' + err.message)
    }
  }

  const handleExportHTML = async () => {
    if (!selectedGraph) return

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const response = await fetch(
        `${apiUrl}/api/export/${selectedGraph.graph_id}/html`
      )
      const data = await response.json()
      
      const blob = new Blob([data.html], { type: 'text/html' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `fsm_${selectedGraph.graph_id}.html`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export error:', err)
      alert('Ошибка экспорта: ' + err.message)
    }
  }

  const handleGenerateCode = async () => {
    if (!localGraph) return

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const response = await fetch(
        `${apiUrl}/api/graph/${graphId}/generate-code`,
        {
          method: 'POST',
        }
      )
      
      if (!response.ok) {
        throw new Error('Ошибка генерации кода')
      }
      
      const data = await response.json()
      setGeneratedCode(data.code)
      setShowCodeModal(true)
    } catch (err) {
      console.error('Generate code error:', err)
      alert('Ошибка генерации кода: ' + err.message)
    }
  }

  if (!selectedGraph) {
    return (
      <div className="empty-state">
        <p>Граф не найден</p>
        <button onClick={() => navigate('/')} className="btn-primary">
          Вернуться на главную
        </button>
      </div>
    )
  }

  return (
    <div className="graph-page">
      <div className="graph-page-header">
        <button onClick={() => navigate('/')} className="back-btn">
          ← Назад
        </button>
        <h2>
          {localGraph.scope} - {localGraph.state_var}
        </h2>
        <div className="header-actions">
          <button
            onClick={() => setIsEditing(!isEditing)}
            className={`edit-mode-btn ${isEditing ? 'active' : ''}`}
          >
            {isEditing ? '✏ Редактирование' : '👁 Просмотр'}
          </button>
          {isEditing && (
            <button onClick={handleGenerateCode} className="generate-code-btn">
              🔄 Сгенерировать код
            </button>
          )}
          <button onClick={handleExportHTML} className="export-btn">
            📄 Экспорт HTML
          </button>
        </div>
      </div>
      
      <PanelGroup direction="vertical">
        <Panel defaultSize={70} minSize={40}>
          <div className="graph-container">
            {isEditing ? (
              <EditableGraphVisualization
                graph={localGraph}
                onGraphChange={handleGraphChange}
                readOnly={false}
              />
            ) : (
              <GraphVisualization graph={localGraph} />
            )}
          </div>
        </Panel>
        <PanelResizeHandle className="resize-handle-horizontal" />
        <Panel defaultSize={30} minSize={20}>
          <DetailsPanel graph={localGraph} />
        </Panel>
      </PanelGroup>
      
      {showCodeModal && generatedCode && (
        <div className="code-modal-overlay" onClick={() => setShowCodeModal(false)}>
          <div className="code-modal" onClick={(e) => e.stopPropagation()}>
            <div className="code-modal-header">
              <h3>Сгенерированный код</h3>
              <button onClick={() => setShowCodeModal(false)}>✕</button>
            </div>
            <div className="code-modal-content">
              <pre><code>{generatedCode}</code></pre>
            </div>
            <div className="code-modal-footer">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(generatedCode)
                  alert('Код скопирован в буфер обмена')
                }}
                className="copy-btn"
              >
                📋 Копировать
              </button>
              <button
                onClick={() => {
                  const blob = new Blob([generatedCode], { type: 'text/plain' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = `generated_${localGraph.scope.replace(/\s+/g, '_')}.sv`
                  document.body.appendChild(a)
                  a.click()
                  document.body.removeChild(a)
                  URL.revokeObjectURL(url)
                }}
                className="download-btn"
              >
                💾 Скачать
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function App() {
  // Загружаем сохраненные данные из localStorage
  const loadFromStorage = () => {
    try {
      const saved = localStorage.getItem('fsm_graphs')
      if (saved) {
        return JSON.parse(saved)
      }
    } catch (e) {
      console.error('Failed to load from localStorage', e)
    }
    return []
  }

  const [code, setCode] = useState(() => {
    try {
      return localStorage.getItem('fsm_code') || ''
    } catch (e) {
      return ''
    }
  })
  const [graphs, setGraphs] = useState(loadFromStorage)
  const [selectedGraphId, setSelectedGraphId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Сохраняем графы в localStorage при изменении
  useEffect(() => {
    try {
      localStorage.setItem('fsm_graphs', JSON.stringify(graphs))
    } catch (e) {
      console.error('Failed to save to localStorage', e)
    }
  }, [graphs])

  // Сохраняем код в localStorage при изменении
  useEffect(() => {
    try {
      localStorage.setItem('fsm_code', code)
    } catch (e) {
      console.error('Failed to save code to localStorage', e)
    }
  }, [code])

  return (
    <BrowserRouter>
      <div className="app">
        <header className="app-header">
          <h1>FSM Graph Visualizer</h1>
          <p>Визуализация конечных автоматов из SystemVerilog кода</p>
        </header>

        <Routes>
          <Route 
            path="/" 
            element={
              <MainPage
                code={code}
                setCode={setCode}
                graphs={graphs}
                setGraphs={setGraphs}
                selectedGraphId={selectedGraphId}
                setSelectedGraphId={setSelectedGraphId}
                loading={loading}
                setLoading={setLoading}
                error={error}
                setError={setError}
              />
            } 
          />
          <Route 
            path="/graph/:graphId" 
            element={
              <GraphPage
                graphs={graphs}
                setGraphs={setGraphs}
                selectedGraphId={selectedGraphId}
                setSelectedGraphId={setSelectedGraphId}
              />
            } 
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
