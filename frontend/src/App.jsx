import { useState, useEffect, useRef } from 'react'
import './App.css'

// Dynamic API base - works in Codespaces and locally
const getApiBase = () => {
  const hostname = window.location.hostname
  
  // GitHub Codespaces: replace port in hostname
  if (hostname.includes('.app.github.dev')) {
    // Current URL is like: verbose-space-telegram-569jwqq995p27q5-3000.app.github.dev
    // We need: verbose-space-telegram-569jwqq995p27q5-8000.app.github.dev
    return window.location.origin.replace('-3000.', '-8000.')
  }
  
  // Local development
  return 'http://localhost:8000'
}

const API_BASE = getApiBase()

const PHASES = [
  { id: 'recon', name: 'Reconnaissance', icon: '🔍', description: 'Scanning target for vulnerabilities' },
  { id: 'plan', name: 'Exploit Planning', icon: '🎯', description: 'Generating exploit strategies' },
  { id: 'attack', name: 'Attack Execution', icon: '⚔️', description: 'Executing exploits' },
  { id: 'analyze', name: 'Code Analysis', icon: '🔬', description: 'Deep code analysis' },
  { id: 'report', name: 'Executive Report', icon: '📊', description: 'Generating summary' },
]

function App() {
  const [timeline, setTimeline] = useState([])
  const [logs, setLogs] = useState([])
  const [stats, setStats] = useState({
    steps: 0,
    maxSteps: 50,
    cumulativeReward: 0,
    status: 'idle',
    totalVulnerabilities: 0,
    totalExploits: 0,
  })
  const [currentPhase, setCurrentPhase] = useState(null)
  const [phasesCompleted, setPhasesCompleted] = useState([])
  const [currentThinking, setCurrentThinking] = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const [lastTimestamp, setLastTimestamp] = useState(0)
  const [targetUrl, setTargetUrl] = useState('http://localhost:5173')
  const [report, setReport] = useState(null)
  const [activeTab, setActiveTab] = useState('timeline')
  const [screenshots, setScreenshots] = useState([])
  const [latestScreenshot, setLatestScreenshot] = useState(null)
  const [sqlInjectionFound, setSqlInjectionFound] = useState(false)
  const timelineEndRef = useRef(null)
  const logsEndRef = useRef(null)
  const pollingIntervalRef = useRef(null)

  const pollLogs = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/logs?since=${lastTimestamp}`)
      const data = await response.json()

      data.logs.forEach(log => {
        if (log.timestamp > lastTimestamp) {
          setLastTimestamp(log.timestamp)
        }

        const message = log.message

        // Add to raw logs
        setLogs(prev => [...prev.slice(-200), { ...log, id: Date.now() + Math.random() }])

        // Track phase changes
        if (log.type === 'phase') {
          const phase = PHASES.find(p => message.toLowerCase().includes(p.id))
          if (phase) {
            setCurrentPhase(phase.id)
          }
        }

        // Parse thinking from logs
        if (message.includes('THINKING:')) {
          const thinking = message.replace(/.*THINKING:/, '').trim()
          setCurrentThinking(prev => ({ ...prev, thinking }))
        } else if (message.includes('ACTION:')) {
          const action = message.replace(/.*ACTION:/, '').trim()
          setCurrentThinking(prev => ({ ...prev, action }))
        } else if (message.includes('PAYLOAD:')) {
          const payload = message.replace(/.*PAYLOAD:/, '').trim()
          setCurrentThinking(prev => ({ ...prev, payload }))
        } else if (message.includes('EXPECTING:')) {
          const expecting = message.replace(/.*EXPECTING:/, '').trim()
          setCurrentThinking(prev => ({ ...prev, expecting }))
        } else if (message.includes('REWARD:')) {
          // Parse reward and add to timeline
          const match = message.match(/REWARD:\s*([-\d.]+)\s*\((.+)\)/)
          if (match && currentThinking) {
            const reward = parseFloat(match[1])
            const reason = match[2]

            // Check for SQL injection success (high reward)
            if (reward >= 1.5 && (reason.toLowerCase().includes('sql') || reason.toLowerCase().includes('injection') || reason.toLowerCase().includes('database'))) {
              setSqlInjectionFound(true)
            }

            setTimeline(prev => [...prev, {
              step: prev.length + 1,
              thinking: currentThinking.thinking || 'No thinking provided',
              action: currentThinking.action || 'unknown',
              payload: currentThinking.payload,
              expecting: currentThinking.expecting,
              reward,
              reason,
              timestamp: new Date().toLocaleTimeString()
            }])

            setStats(prev => ({
              ...prev,
              steps: prev.steps + 1,
              cumulativeReward: prev.cumulativeReward + reward
            }))

            setCurrentThinking(null)
          }
        }
        
        // Detect SQL injection or mission complete messages
        if (message.includes('MISSION COMPLETE') || message.includes('SQL injection') || message.includes("' OR '1'='1'")) {
          setSqlInjectionFound(true)
        }

        // Check for status messages
        if (log.type === 'status') {
          if (log.message === 'starting') {
            setIsRunning(true)
            setStats(prev => ({ ...prev, status: 'running' }))
          } else if (log.message === 'completed') {
            if (log.phase) {
              setPhasesCompleted(prev => [...new Set([...prev, log.phase])])
            }
          } else if (log.message === 'failed') {
            // Don't stop on individual phase failure
          }
          
          // Check for pipeline completion
          if (message.includes('Pipeline completed')) {
            setIsRunning(false)
            setStats(prev => ({ ...prev, status: 'completed' }))
            fetchReport()
            fetchStats()
          }
        }
      })
    } catch (error) {
      console.error('Error polling logs:', error)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/stats`)
      const data = await response.json()
      setStats(prev => ({
        ...prev,
        totalVulnerabilities: data.total_vulnerabilities || 0,
        totalExploits: data.total_exploits || 0,
      }))
    } catch (error) {
      console.error('Error fetching stats:', error)
    }
  }

  const fetchReport = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/report`)
      const data = await response.json()
      if (data.report) {
        setReport(data.report)
      }
    } catch (error) {
      console.error('Error fetching report:', error)
    }
  }

  useEffect(() => {
    // Start polling when component mounts
    pollingIntervalRef.current = setInterval(pollLogs, 500) // Poll every 500ms

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
      }
    }
  }, [lastTimestamp, currentThinking])

  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [timeline])

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const runFullPipeline = async () => {
    setTimeline([])
    setLogs([])
    setPhasesCompleted([])
    setCurrentPhase(null)
    setReport(null)
    setScreenshots([])
    setLatestScreenshot(null)
    setSqlInjectionFound(false)
    setStats({ steps: 0, maxSteps: 50, cumulativeReward: 0, status: 'running', totalVulnerabilities: 0, totalExploits: 0 })
    setCurrentThinking(null)
    setLastTimestamp(0)
    setIsRunning(true)

    try {
      await fetch(`${API_BASE}/api/run/full-pipeline?target_url=${encodeURIComponent(targetUrl)}&demo_mode=true`, { method: 'POST' })
    } catch (error) {
      console.error('Error running pipeline:', error)
      setIsRunning(false)
      setStats(prev => ({ ...prev, status: 'failed' }))
    }
  }

  const runAgent = async () => {
    setTimeline([])
    setLogs([])
    setStats({ steps: 0, maxSteps: 50, cumulativeReward: 0, status: 'running', totalVulnerabilities: 0, totalExploits: 0 })
    setCurrentThinking(null)
    setLastTimestamp(0)

    try {
      await fetch(`${API_BASE}/api/run/recon?target_url=${encodeURIComponent(targetUrl)}`, { method: 'POST' })
    } catch (error) {
      console.error('Error running agent:', error)
    }
  }

  const resetAgent = async () => {
    if (!confirm('Clear all data and reset?')) return

    try {
      await fetch(`${API_BASE}/api/reset`, { method: 'POST' })
      setTimeline([])
      setLogs([])
      setPhasesCompleted([])
      setCurrentPhase(null)
      setReport(null)
      setStats({ steps: 0, maxSteps: 50, cumulativeReward: 0, status: 'idle', totalVulnerabilities: 0, totalExploits: 0 })
      setCurrentThinking(null)
      setLastTimestamp(0)
    } catch (error) {
      console.error('Error resetting:', error)
    }
  }

  const getRewardColor = (reward) => {
    if (reward >= 0.8) return 'reward-high'
    if (reward >= 0.3) return 'reward-medium'
    if (reward >= 0) return 'reward-low'
    return 'reward-negative'
  }

  return (
    <div className="app">
      {/* SQL Injection Success Banner */}
      {sqlInjectionFound && (
        <div className="sql-injection-banner">
          <span className="banner-icon">🎯</span>
          <span className="banner-text">CRITICAL VULNERABILITY FOUND: SQL Injection Successful!</span>
          <span className="banner-icon">💀</span>
        </div>
      )}
      
      <header className="header">
        <h1>🛡️ AI Security Testing Suite</h1>
        <p className="subtitle">Automated Penetration Testing with Reinforcement Learning</p>
        
        {/* Target URL Input */}
        <div className="target-input">
          <label>Target URL:</label>
          <input
            type="text"
            value={targetUrl}
            onChange={(e) => setTargetUrl(e.target.value)}
            placeholder="http://localhost:5173"
            disabled={isRunning}
          />
        </div>

        {/* Phase Progress */}
        <div className="phase-progress">
          {PHASES.map((phase, idx) => (
            <div
              key={phase.id}
              className={`phase-item ${currentPhase === phase.id ? 'active' : ''} ${phasesCompleted.includes(phase.id) ? 'completed' : ''}`}
            >
              <span className="phase-icon">{phase.icon}</span>
              <span className="phase-name">{phase.name}</span>
              {phasesCompleted.includes(phase.id) && <span className="phase-check">✓</span>}
            </div>
          ))}
        </div>

        <div className="stats-bar">
          <div className="stat">
            <span className="stat-label">Steps</span>
            <span className="stat-value">{stats.steps}/{stats.maxSteps}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Reward</span>
            <span className="stat-value">{stats.cumulativeReward.toFixed(2)}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Vulns Found</span>
            <span className="stat-value vuln-count">{stats.totalVulnerabilities}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Exploits</span>
            <span className="stat-value exploit-count">{stats.totalExploits}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Status</span>
            <span className={`stat-value status-${stats.status}`}>
              {stats.status === 'running' && '🔄 Running'}
              {stats.status === 'completed' && '✅ Complete'}
              {stats.status === 'failed' && '❌ Failed'}
              {stats.status === 'idle' && '⏸️ Idle'}
            </span>
          </div>
        </div>
      </header>

      <div className="controls">
        <button
          className="btn-primary"
          onClick={runFullPipeline}
          disabled={isRunning}
        >
          {isRunning ? '⏳ Running Pipeline...' : '🚀 Run Full Pipeline'}
        </button>
        <button
          className="btn-secondary"
          onClick={runAgent}
          disabled={isRunning}
        >
          🔍 Recon Only
        </button>
        <button
          className="btn-danger"
          onClick={resetAgent}
          disabled={isRunning}
        >
          🗑️ Reset
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="tab-nav">
        <button className={`tab ${activeTab === 'timeline' ? 'active' : ''}`} onClick={() => setActiveTab('timeline')}>
          📊 Timeline
        </button>
        <button className={`tab ${activeTab === 'logs' ? 'active' : ''}`} onClick={() => setActiveTab('logs')}>
          📜 Logs ({logs.length})
        </button>
        <button className={`tab ${activeTab === 'report' ? 'active' : ''}`} onClick={() => setActiveTab('report')}>
          📄 Report {report ? '✓' : ''}
        </button>
      </div>

      {currentThinking && (
        <div className="thinking-box">
          <h3>💭 Agent Thinking...</h3>
          <p className="thinking-text">{currentThinking.thinking}</p>
          {currentThinking.action && (
            <div className="thinking-action">
              <span className="label">Action:</span> {currentThinking.action}
            </div>
          )}
          {currentThinking.payload && (
            <div className="thinking-payload">
              <span className="label">Payload:</span> <code>{currentThinking.payload}</code>
            </div>
          )}
          {currentThinking.expecting && (
            <div className="thinking-expecting">
              <span className="label">Expecting:</span> {currentThinking.expecting}
            </div>
          )}
        </div>
      )}

      {/* Timeline Tab */}
      {activeTab === 'timeline' && (
        <div className="timeline">
          <h2>📊 Action Timeline</h2>
          {timeline.length === 0 ? (
            <div className="empty-state">
              <p>No steps yet. Click "Run Full Pipeline" to start security testing.</p>
            </div>
          ) : (
            <div className="timeline-list">
              {timeline.map((item, i) => (
                <div key={i} className="timeline-item">
                  <div className="timeline-header">
                    <span className="step-number">Step {item.step}</span>
                    <span className="timestamp">{item.timestamp}</span>
                  </div>
                  <div className="timeline-thinking">{item.thinking}</div>
                  <div className="timeline-details">
                    <span className="action-badge">{item.action}</span>
                    {item.payload && <code className="payload-code">{item.payload}</code>}
                  </div>
                  <div className={`timeline-reward ${getRewardColor(item.reward)}`}>
                    <span className="reward-value">💰 {item.reward > 0 ? '+' : ''}{item.reward}</span>
                    <span className="reward-reason">{item.reason}</span>
                  </div>
                </div>
              ))}
              <div ref={timelineEndRef} />
            </div>
          )}
        </div>
      )}

      {/* Logs Tab */}
      {activeTab === 'logs' && (
        <div className="logs-panel">
          <h2>📜 Raw Logs</h2>
          <div className="logs-list">
            {logs.map((log) => (
              <div key={log.id} className={`log-entry log-${log.type}`}>
                <span className="log-time">{new Date(log.timestamp * 1000).toLocaleTimeString()}</span>
                <span className="log-script">[{log.script}]</span>
                <span className="log-message">{log.message}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}

      {/* Report Tab */}
      {activeTab === 'report' && (
        <div className="report-panel">
          <h2>📄 Executive Report</h2>
          {report ? (
            <div className="report-content">
              <pre>{report}</pre>
            </div>
          ) : (
            <div className="empty-state">
              <p>No report generated yet. Complete a full pipeline run to generate an executive report.</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default App
