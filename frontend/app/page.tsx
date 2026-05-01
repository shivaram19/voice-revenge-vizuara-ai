const navItems = [
  { label: 'Home', active: true },
  { label: 'Live', active: true },
  { label: 'Pipeline' },
  { label: 'Contacts' },
  { label: 'Automations' },
  { label: 'Analytics' }
];

const interactions = [
  {
    id: 'VC-301',
    caller: 'Northwind Electric',
    queue: 'Emergency',
    timer: '00:12',
    status: 'Ringing',
    priority: 'NeedsAttention',
    stage: 'Discovery',
    badges: ['High intent']
  },
  {
    id: 'VC-304',
    caller: 'Coral Ridge',
    queue: 'Callback',
    timer: '08:41',
    status: 'Live',
    priority: 'Now',
    stage: 'Qualification',
    badges: ['Intent confirmed']
  },
  {
    id: 'VC-278',
    caller: 'Southgate',
    queue: 'Pipeline',
    timer: '03:19',
    status: 'WrapUp',
    priority: 'AtRisk',
    stage: 'Negotiation',
    badges: ['Missing follow-up']
  }
];

const pipelineStages = [
  {
    name: 'New',
    cards: [
      { id: 'VC-301', owner: 'Lena', need: 'Verify site access' },
      { id: 'VC-302', owner: 'Kai', need: 'Send pricing deck' }
    ]
  },
  {
    name: 'Connected',
    cards: [
      { id: 'VC-303', owner: 'Mira', need: 'Schedule demo' },
      { id: 'VC-304', owner: 'Lena', need: 'Confirm service slot' }
    ]
  },
  {
    name: 'Qualified',
    cards: [{ id: 'VC-305', owner: 'Kai', need: 'Gather compliance docs' }]
  },
  {
    name: 'Booked',
    cards: [{ id: 'VC-306', owner: 'Mira', need: 'Log meeting link' }]
  }
];

const transcriptLines = [
  { speaker: 'Caller', text: 'We need a 2 PM site walk.', time: '00:23', certainty: 'high' },
  { speaker: 'Agent', text: 'I am connecting you with our field engineer.', time: '00:37', certainty: 'clean' },
  { speaker: 'Agent', text: 'Are you still on the site now?', time: '00:44', certainty: 'medium' }
];

const supervisorStats = [
  { label: 'Queue Load', value: '18/22', detail: 'Live calls vs capacity' },
  { label: 'At Risk SLA', value: '3', detail: 'Calls > 90s wait' },
  { label: 'Coachable Moments', value: '5', detail: 'Need feedback' },
  { label: 'Callbacks', value: '6', detail: 'Pending follow-up' }
];

const agentRows = [
  { agent: 'Lena', calls: 5, handle: '4:12', transfer: '2%', state: 'Ready' },
  { agent: 'Kai', calls: 4, handle: '5:05', transfer: '4%', state: 'Live' },
  { agent: 'Mira', calls: 6, handle: '3:33', transfer: '1%', state: 'WrapUp' }
];

const shortcuts = [
  { key: 'A', action: 'Accept' },
  { key: 'H', action: 'Hold' },
  { key: 'T', action: 'Transfer' },
  { key: '/', action: 'Search interactions' },
  { key: 'G', action: 'Jump to pipeline' }
];

const alerts = [
  'P1 waiting over SLA threshold',
  'Repeated barge-in sessions detected',
  'Stale wrap-up tasks for VC-278'
];

export default function Page() {
  return (
    <div className="page">
      <header className="hero">
        <div>
          <p className="hero-meta">Voice CRM Cockpit | Operator-first | Live + Pipeline</p>
          <h1>Live calls, recommended next actions, and pipeline momentum in one pane.</h1>
        </div>
        <div className="hero-meta">
          <span>Now / NeedsAttention / AtRisk</span>
          <span>Slack-style focus, CRM rigor</span>
        </div>
        <div className="status-stack">
          <span className="status-pill">Live priority</span>
          <span className="status-pill">Stage validation</span>
          <span className="status-pill">Transcript auto-scroll</span>
        </div>
      </header>

      <div className="cockpit-grid">
        <aside className="left-rail">
          <nav>
            {navItems.map((item) => (
              <button key={item.label} className={item.active ? 'active' : ''}>
                {item.label}
              </button>
            ))}
          </nav>
          <div className="density-toggle">
            <span>Comfortable</span>
            <span>Compact</span>
          </div>
        </aside>

        <section className="center-stream">
          <div className="stream-header">
            <div>
              <strong>Live interactions</strong>
              <p className="text-muted">Queue: Emergency | Barge-in signals flagged</p>
            </div>
            <div className="filters">
              <span className="filter-pill">NeedsAttention</span>
              <span className="filter-pill">Callbacks</span>
            </div>
          </div>
          <div className="stream-list">
            {interactions.map((interaction) => (
              <div key={interaction.id} className="interaction-row">
                <div>
                  <strong>{interaction.caller}</strong>
                  <div className="interaction-meta">
                    <span>
                      {interaction.queue} | {interaction.stage}
                    </span>
                    <span>{interaction.badges.join(' | ')}</span>
                  </div>
                </div>
                <div>
                  <span className="status-chip">{interaction.status}</span>
                </div>
                <div>
                  <span>{interaction.timer}</span>
                </div>
              </div>
            ))}
          </div>
          <div className="shortcut">
            {shortcuts.map((shortcut) => (
              <button key={shortcut.key}>
                {shortcut.key} | {shortcut.action}
              </button>
            ))}
            <span>Keyboard-first for rapid actions</span>
          </div>
        </section>

        <aside className="right-panel">
          <div className="call-controls">
            <div>
              <strong>Call controls</strong>
            </div>
            <div className="call-status">
              <span className="status-chip">Live</span>
              <span>Agent-facing transcript</span>
            </div>
            <div>
              <button>Accept</button>
              <button>Hold</button>
              <button>Transfer</button>
              <button>End</button>
            </div>
          </div>
          <div className="transcript">
            <div className="transcript-header">
              <p>Transcript (auto-scroll)</p>
              <button>Freeze</button>
            </div>
            {transcriptLines.map((line) => (
              <div key={`${line.speaker}-${line.time}`} className="transcript-line">
                <span>
                  <strong>{line.speaker}</strong> | {line.text}
                </span>
                <span>{line.time}</span>
              </div>
            ))}
          </div>
          <div className="contact-card">
            <strong>Contact 360 | Northwind Electric</strong>
            <p>Owner: Lena</p>
            <p>Previous calls: 4 | Last disposition: Inquiry</p>
            <p>Next action recommended: Book site survey | high urgency</p>
            <div className="bottom-actions">
              <button>Summarize</button>
              <button>Escalate</button>
              <button>Assign owner</button>
              <button>Submit disposition</button>
            </div>
          </div>
        </aside>
      </div>

      <section className="pipeline-board">
        <header className="stream-header">
          <div>
            <strong>Pipeline board</strong>
            <p className="text-muted">Drag-to-stage with drop validation | required fields inline</p>
          </div>
          <div className="filters">
            <span className="filter-pill">Stage filter: All</span>
            <span className="filter-pill">Owner: Ops</span>
            <span className="filter-pill">Time range: 90d</span>
          </div>
        </header>
        <div className="pipeline-grid">
          {pipelineStages.map((stage) => (
            <div key={stage.name} className="stage-column">
              <strong>{stage.name}</strong>
              {stage.cards.map((card) => (
                <div key={card.id} className="stage-card">
                  <span>{card.id}</span>
                  <span>Owner: {card.owner}</span>
                  <span>Need: {card.need}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </section>

      <section className="conversation-detail">
        <div className="transcript">
          <div className="transcript-header">
            <p>Conversation detail</p>
            <button>Freeze</button>
          </div>
          {transcriptLines.map((line) => (
            <div key={line.text + line.time} className="transcript-line">
              <span>
                <strong>{line.speaker}</strong> | {line.text}
              </span>
              <span>{line.time}</span>
            </div>
          ))}
          <div className="bottom-actions">
            <button>Summarize</button>
            <button>Escalate</button>
            <button>Assign owner</button>
            <button>Submit disposition</button>
          </div>
        </div>
        <div className="contact-card">
          <strong>Extraction & CRM context</strong>
          <p>Intent: Site walk | Urgency: High</p>
          <p>Next-best action: Confirm 2 PM slot</p>
          <p>Required follow-up fields: Owner, Follow-up channel</p>
        </div>
      </section>

      <section className="supervisor">
        <header className="stream-header">
          <div>
            <strong>Supervisor queue view</strong>
            <p className="text-muted">SLA, coaching flags, backlog alerts</p>
          </div>
        </header>
        <div className="stats-grid">
          {supervisorStats.map((stat) => (
            <div key={stat.label} className="stats-card">
              <span>{stat.label}</span>
              <strong>{stat.value}</strong>
              <p>{stat.detail}</p>
            </div>
          ))}
        </div>
        <table className="team-table">
          <thead>
            <tr>
              <th>Agent</th>
              <th>Active</th>
              <th>Avg handle</th>
              <th>Transfer %</th>
              <th>State</th>
            </tr>
          </thead>
          <tbody>
            {agentRows.map((row) => (
              <tr key={row.agent}>
                <td>{row.agent}</td>
                <td>{row.calls}</td>
                <td>{row.handle}</td>
                <td>{row.transfer}</td>
                <td>{row.state}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="contact-card">
          <strong>Alert feed</strong>
          <ul>
            {alerts.map((alert) => (
              <li key={alert}>{alert}</li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
