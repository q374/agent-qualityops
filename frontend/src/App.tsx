import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from 'react'
import { api, ApiError } from './api'
import type { CompareData, EvalCase, EvalResult, EvalRun, HumanReview, PromptVersion, ReleaseGateData, Summary } from './types'

type PageId = 'overview' | 'cases' | 'runs' | 'badcases' | 'release'
type IconName = PageId | 'refresh' | 'arrow' | 'check' | 'alert' | 'download' | 'plus' | 'close' | 'shield' | 'clock' | 'search'

const nav: Array<{ id: PageId; label: string; hint: string }> = [
  { id: 'overview', label: '质量概览', hint: '全局健康度' },
  { id: 'cases', label: '评测集', hint: '数据与来源' },
  { id: 'runs', label: '版本与运行', hint: '对照实验' },
  { id: 'badcases', label: 'Badcase 审核', hint: '问题归因' },
  { id: 'release', label: '发布门禁', hint: '决策与报告' },
]

const iconPaths: Record<IconName, ReactNode> = {
  overview: <><path d="M4 13h6V4H4zM14 20h6V11h-6zM4 20h6v-3H4zM14 7h6V4h-6z" /></>,
  cases: <><path d="M5 4h14v16H5z" /><path d="M9 8h6M9 12h6M9 16h4" /></>,
  runs: <><path d="M5 5h5v5H5zM14 14h5v5h-5zM14 5h5v5h-5zM5 14h5v5H5z" /><path d="M10 7.5h4M16.5 10v4M14 16.5h-4M7.5 14v-4" /></>,
  badcases: <><path d="M12 3 3.7 18h16.6z" /><path d="M12 9v4M12 16h.01" /></>,
  release: <><path d="M12 3 5 6v5c0 4.8 3 8 7 10 4-2 7-5.2 7-10V6z" /><path d="m9 12 2 2 4-4" /></>,
  refresh: <><path d="M20 11a8 8 0 1 0-2.3 5.7" /><path d="M20 5v6h-6" /></>,
  arrow: <><path d="M5 12h14M15 8l4 4-4 4" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  alert: <><path d="M12 3 3.7 18h16.6z" /><path d="M12 9v4M12 16h.01" /></>,
  download: <><path d="M12 3v12m0 0 4-4m-4 4-4-4" /><path d="M5 20h14" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  shield: <><path d="M12 3 5 6v5c0 4.8 3 8 7 10 4-2 7-5.2 7-10V6z" /><path d="m9 12 2 2 4-4" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4 4" /></>,
}

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{iconPaths[name]}</svg>
}

function cn(...parts: Array<string | false | null | undefined>) { return parts.filter(Boolean).join(' ') }
function fmtNum(value: number | undefined, digits = 0) { return Number.isFinite(value) ? Number(value).toFixed(digits) : '—' }
function fmtDate(value?: string | null) { return value ? new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value)) : '—' }
function percent(value: unknown) {
  if (typeof value !== 'number') return '—'
  return `${(value <= 1 ? value * 100 : value).toFixed(1)}%`
}
function getError(error: unknown) { return error instanceof Error ? error.message : '发生未知错误' }
function titleFor(page: PageId) { return nav.find((item) => item.id === page)?.label || '' }

function Spinner() { return <span className="spinner" aria-label="加载中" /> }
function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'good' | 'warn' | 'bad' | 'blue' }) { return <span className={`badge badge-${tone}`}>{children}</span> }
function StatusBadge({ status }: { status?: string | null }) {
  const map: Record<string, { label: string; tone: 'neutral' | 'good' | 'warn' | 'bad' | 'blue' }> = {
    completed: { label: '已完成', tone: 'good' }, running: { label: '运行中', tone: 'blue' }, pending: { label: '等待中', tone: 'neutral' },
    failed: { label: '失败', tone: 'bad' }, budget_exceeded: { label: '预算中止', tone: 'warn' }, approved: { label: '已通过', tone: 'good' },
    rejected: { label: '已驳回', tone: 'bad' }, pending_review: { label: '待审核', tone: 'warn' },
  }
  const meta = map[status || ''] || { label: status || '未知', tone: 'neutral' as const }
  return <Badge tone={meta.tone}>{meta.label}</Badge>
}
function Panel({ title, subtitle, action, children, className }: { title?: string; subtitle?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={cn('panel', className)}>{(title || action) && <header className="panel-head"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</header>}<div className="panel-body">{children}</div></section>
}
function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return <div className="state state-error"><span className="state-icon"><Icon name="alert" size={22} /></span><div><strong>数据加载失败</strong><p>{message}</p></div>{retry && <button className="btn btn-secondary" onClick={retry}><Icon name="refresh" />重试</button>}</div>
}
function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="empty"><div className="empty-mark"><span /><span /><span /></div><h3>{title}</h3><p>{description}</p>{action}</div>
}
function LoadingRows() { return <div className="skeleton-wrap">{[1, 2, 3].map((n) => <div className="skeleton-row" key={n}><span /><span /><span /></div>)}</div> }

function useLoad<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const refresh = useCallback(async () => {
    setLoading(true); setError('')
    try { setData(await loader()) } catch (e) { setError(getError(e)) } finally { setLoading(false) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(() => { void refresh() }, [refresh])
  return { data, setData, loading, error, refresh }
}

function Metric({ label, value, hint, tone = 'default' }: { label: string; value: ReactNode; hint: string; tone?: string }) {
  return <div className={`metric metric-${tone}`}><div className="metric-top"><span>{label}</span><i /></div><strong>{value}</strong><p>{hint}</p></div>
}

function OverviewPage({ navigate }: { navigate: (page: PageId) => void }) {
  const summary = useLoad<Summary>(() => api.summary(), [])
  const runs = useLoad<EvalRun[]>(api.runs, [])
  const latest = summary.data?.latest_run || summary.data?.latest_runs?.[0] || runs.data?.[0]
  const latestComplete = runs.data?.find((run) => run.status === 'completed')
  return <div className="page-grid">
    {(summary.error || runs.error) && <ErrorState message={summary.error || runs.error} retry={() => { void summary.refresh(); void runs.refresh() }} />}
    <section className="hero">
      <div><Badge tone="blue"><span className="pulse-dot" />企业智能体质量中枢</Badge><h1>让每一次模型升级，<br /><em>都有证据再发布。</em></h1><p>统一管理评测数据、版本实验、问题归因与发布门禁。所有结论都可追溯到真实用例与人工判断。</p><div className="hero-actions"><button className="btn btn-primary" onClick={() => navigate('runs')}>发起版本评测<Icon name="arrow" /></button><button className="btn btn-secondary" onClick={() => navigate('cases')}>管理评测集</button></div></div>
      <div className="hero-visual" aria-hidden="true"><div className="ring ring-a" /><div className="ring ring-b" /><div className="core"><Icon name="shield" size={30} /><b>QUALITY</b><span>证据驱动</span></div><div className="orbit orbit-a">01</div><div className="orbit orbit-b">50</div><div className="orbit orbit-c">PASS</div></div>
    </section>
    <div className="metrics-grid">
      <Metric label="评测用例" value={summary.loading ? '…' : (summary.data?.case_count ?? summary.data?.counts?.cases ?? '—')} hint="带来源的离线测试资产" />
      <Metric label="Prompt 版本" value={summary.loading ? '…' : (summary.data?.version_count ?? summary.data?.counts?.versions ?? '—')} hint="配置与实验版本留痕" />
      <Metric label="累计运行" value={summary.loading ? '…' : (summary.data?.run_count ?? summary.data?.counts?.runs ?? runs.data?.length ?? '—')} hint="包含演示与真实模型运行" />
      <Metric label="人工审核记录" value={summary.loading ? '…' : (summary.data?.pending_review_count ?? summary.data?.counts?.reviews ?? '—')} hint="全部判断都有据可查" tone="amber" />
    </div>
    <div className="two-col">
      <Panel title="最近评测运行" subtitle="模型版本的执行与费用状态" action={<button className="text-btn" onClick={() => navigate('runs')}>查看全部 <Icon name="arrow" size={15} /></button>}>
        {runs.loading ? <LoadingRows /> : runs.data?.length ? <div className="run-list">{runs.data.slice(0, 5).map((run) => <div className="run-row" key={run.id}><div className="run-id"><span>R{String(run.id).padStart(3, '0')}</span><div><strong>版本 #{run.prompt_version_id}</strong><small>{fmtDate(run.started_at)}</small></div></div><StatusBadge status={run.status} /><div className="run-cost">¥{fmtNum(run.spent_cny, 3)}</div></div>)}</div> : <EmptyState title="还没有评测运行" description="创建两个 Prompt 版本后即可开始对照实验。" action={<button className="btn btn-secondary" onClick={() => navigate('runs')}>配置版本</button>} />}
      </Panel>
      <Panel title="发布准备度" subtitle="默认质量门禁的当前状态">
        <div className="readiness">
          <div className="readiness-score"><div className="score-ring"><strong>{latestComplete ? '待判定' : '—'}</strong></div><p>{latestComplete ? `基于运行 R${latestComplete.id}` : '完成候选版本评测后生成'}</p></div>
          <div className="gate-mini">
            {[['高风险安全失败', '0 个'], ['依据正确率', '≥ 90%'], ['任务完成率', '≥ 80%'], ['严重回归', '≤ 3 条']].map(([k, v]) => <div key={k}><span><i />{k}</span><b>{v}</b></div>)}
          </div>
          <button className="btn btn-dark block" onClick={() => navigate('release')}>进入发布决策台<Icon name="arrow" /></button>
        </div>
      </Panel>
    </div>
    {latest?.error_message && <div className="inline-warning"><Icon name="alert" /><span>最近运行异常：{latest.error_message}</span></div>}
  </div>
}

function CasesPage() {
  const resource = useLoad<EvalCase[]>(api.cases, [])
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('all')
  const [showImport, setShowImport] = useState(false)
  const [importText, setImportText] = useState('')
  const [importError, setImportError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const categories = useMemo(() => Array.from(new Set(resource.data?.map((c) => c.category) || [])), [resource.data])
  const filtered = useMemo(() => (resource.data || []).filter((item) => (category === 'all' || item.category === category) && `${item.title} ${item.input_text} ${item.external_id}`.toLowerCase().includes(query.toLowerCase())), [resource.data, query, category])
  async function importData() {
    setImportError('')
    try {
      const parsed = JSON.parse(importText)
      const list = Array.isArray(parsed) ? parsed : parsed.cases
      if (!Array.isArray(list) || !list.length) throw new Error('JSON 顶层应为非空数组，或包含 cases 数组。')
      setSubmitting(true)
      await api.importCases(list)
      setShowImport(false); setImportText(''); await resource.refresh()
    } catch (e) { setImportError(getError(e)) } finally { setSubmitting(false) }
  }
  return <div className="page-grid">
    <div className="page-heading"><div><span className="eyebrow">DATASET GOVERNANCE</span><h1>评测集</h1><p>每条用例都保留预期行为、风险等级与公开来源，保证结论可复核。</p></div><button className="btn btn-primary" onClick={() => setShowImport(true)}><Icon name="plus" />导入用例</button></div>
    <div className="dataset-summary"><div><b>{resource.data?.length ?? '—'}</b><span>用例总数</span></div>{Object.entries(categoryLabels).map(([key, name]) => <div key={key}><b>{resource.data?.filter((v) => v.category === key).length ?? '—'}</b><span>{name}</span></div>)}</div>
    <Panel>
      <div className="toolbar"><label className="search"><Icon name="search" /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索标题、问题或用例 ID" /></label><select value={category} onChange={(e) => setCategory(e.target.value)}><option value="all">全部分类</option>{categories.map((v) => <option value={v} key={v}>{categoryLabels[v] || v}</option>)}</select><button className="icon-btn" onClick={() => void resource.refresh()} aria-label="刷新"><Icon name="refresh" /></button></div>
      {resource.loading ? <LoadingRows /> : resource.error ? <ErrorState message={resource.error} retry={() => void resource.refresh()} /> : !resource.data?.length ? <EmptyState title="评测集还是空的" description="导入带来源、参考答案和预期行为的 JSON 用例后即可开始评测。" action={<button className="btn btn-primary" onClick={() => setShowImport(true)}>导入第一批用例</button>} /> : !filtered.length ? <EmptyState title="没有匹配用例" description="调整搜索词或分类筛选条件。" /> : <div className="table-scroll"><table><thead><tr><th>用例</th><th>分类</th><th>风险</th><th>预期行为</th><th>来源</th></tr></thead><tbody>{filtered.map((item) => <tr key={item.id}><td className="case-main"><small>{item.external_id}</small><strong>{item.title}</strong><p>{item.input_text}</p></td><td><Badge tone="blue">{categoryLabels[item.category] || item.category}</Badge></td><td><Badge tone={item.risk_level === 'high' ? 'bad' : item.risk_level === 'medium' ? 'warn' : 'neutral'}>{item.risk_level === 'high' ? '高' : item.risk_level === 'medium' ? '中' : '低'}</Badge></td><td className="muted-cell">{item.expected_behavior}</td><td>{item.source_url ? <a className="source-link" href={item.source_url} target="_blank" rel="noreferrer">{item.source_title || '查看来源'} ↗</a> : <span className="muted">未提供</span>}</td></tr>)}</tbody></table></div>}
    </Panel>
    {showImport && <Modal title="导入评测用例" onClose={() => setShowImport(false)}><p className="form-note">粘贴 JSON 数组。字段遵循 API 契约；系统不会自动扩写或改写原始内容。</p><label className="field"><span>JSON 数据</span><textarea rows={14} value={importText} onChange={(e) => setImportText(e.target.value)} placeholder={'[\n  { "external_id": "OPS-001", "title": "..." }\n]'} /></label>{importError && <p className="field-error"><Icon name="alert" size={15} />{importError}</p>}<div className="modal-actions"><button className="btn btn-secondary" onClick={() => setShowImport(false)}>取消</button><button className="btn btn-primary" disabled={submitting || !importText.trim()} onClick={() => void importData()}>{submitting && <Spinner />}确认导入</button></div></Modal>}
  </div>
}

function RunsPage() {
  const versions = useLoad<PromptVersion[]>(api.versions, [])
  const runs = useLoad<EvalRun[]>(api.runs, [])
  const [showVersion, setShowVersion] = useState(false)
  const [selected, setSelected] = useState<number[]>([])
  const [mode, setMode] = useState('demo')
  const [budget, setBudget] = useState(5)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const [baseline, setBaseline] = useState(0)
  const [candidate, setCandidate] = useState(0)
  const compare = useLoad<CompareData | null>(() => baseline && candidate ? api.compare(baseline, candidate) : Promise.resolve(null), [baseline, candidate])
  const completed = runs.data?.filter((r) => r.status === 'completed') || []
  async function startRun() {
    if (selected.length !== 2) { setActionError('请选择恰好两个版本进行对照评测。'); return }
    setBusy(true); setActionError('')
    try { await api.createRun({ version_ids: selected, mode, budget_cny: budget }); await runs.refresh() } catch (e) { setActionError(getError(e)) } finally { setBusy(false) }
  }
  return <div className="page-grid">
    <div className="page-heading"><div><span className="eyebrow">CONTROLLED EXPERIMENT</span><h1>版本与运行</h1><p>固定评测集与预算，让基线和候选版本在同一尺度上竞争。</p></div><button className="btn btn-secondary" onClick={() => setShowVersion(true)}><Icon name="plus" />新建版本</button></div>
    {(versions.error || runs.error) && <ErrorState message={versions.error || runs.error} retry={() => { void versions.refresh(); void runs.refresh() }} />}
    <div className="two-col runs-layout">
      <Panel title="Prompt 版本" subtitle="选择两个版本后发起批量评测">
        {versions.loading ? <LoadingRows /> : !versions.data?.length ? <EmptyState title="还没有 Prompt 版本" description="先创建基线与候选版本。密钥只从后端本地环境读取。" action={<button className="btn btn-primary" onClick={() => setShowVersion(true)}>新建版本</button>} /> : <div className="version-list">{versions.data.map((v) => <label className={cn('version-card', selected.includes(v.id) && 'selected')} key={v.id}><input type="checkbox" checked={selected.includes(v.id)} onChange={() => setSelected((old) => old.includes(v.id) ? old.filter((id) => id !== v.id) : old.length < 2 ? [...old, v.id] : old)} /><div className="version-check"><Icon name="check" size={13} /></div><div><div className="version-title"><strong>{v.name}</strong>{v.is_baseline && <Badge tone="neutral">基线</Badge>}</div><p>{v.model} · Temperature {v.temperature}</p><small>{v.system_prompt}</small></div></label>)}</div>}
        <div className="run-config"><div className="segmented"><button className={mode === 'demo' ? 'active' : ''} onClick={() => setMode('demo')}>离线演示</button><button className={mode === 'deepseek' ? 'active' : ''} onClick={() => setMode('deepseek')}>DeepSeek</button></div><label><span>预算上限</span><div className="money-input">¥<input type="number" min="0.1" max="5" step="0.1" value={budget} onChange={(e) => setBudget(Number(e.target.value))} /></div></label><button className="btn btn-primary block" disabled={busy || selected.length !== 2} onClick={() => void startRun()}>{busy ? <Spinner /> : <Icon name="runs" />}运行两个版本</button>{mode === 'deepseek' && <p className="secure-note"><Icon name="shield" size={14} />真实模型密钥由后端环境变量读取，前端不接触密钥。</p>}{actionError && <p className="field-error"><Icon name="alert" size={15} />{actionError}</p>}</div>
      </Panel>
      <Panel title="运行记录" subtitle="费用、状态和异常均完整留痕" action={<button className="icon-btn" onClick={() => void runs.refresh()} aria-label="刷新"><Icon name="refresh" /></button>}>
        {runs.loading ? <LoadingRows /> : !runs.data?.length ? <EmptyState title="暂无运行记录" description="选择两个版本并运行后，结果会显示在这里。" /> : <div className="run-list detailed">{runs.data.map((run) => <div className="run-row" key={run.id}><div className="run-id"><span>R{String(run.id).padStart(3, '0')}</span><div><strong>版本 #{run.prompt_version_id}</strong><small>{run.mode === 'demo' ? '离线演示' : run.mode} · {fmtDate(run.started_at)}</small></div></div><div><StatusBadge status={run.status} />{run.error_message && <small className="error-copy">{run.error_message}</small>}</div><div className="run-cost"><strong>¥{fmtNum(run.spent_cny, 3)}</strong><small>{run.case_count ? `${run.case_count} 条` : ''}</small></div></div>)}</div>}
      </Panel>
    </div>
    <Panel title="版本对比" subtitle="选择两次已完成运行，识别进步与回归">
      <div className="compare-controls"><SelectRun label="基线运行" value={baseline} setValue={setBaseline} runs={completed} /><span className="compare-arrow"><Icon name="arrow" /></span><SelectRun label="候选运行" value={candidate} setValue={setCandidate} runs={completed} /></div>
      {!baseline || !candidate ? <EmptyState title="选择对照运行" description="完成至少两次评测后，选择基线与候选运行查看指标差异。" /> : compare.loading ? <LoadingRows /> : compare.error ? <ErrorState message={compare.error} retry={() => void compare.refresh()} /> : compare.data ? <CompareView data={compare.data} /> : null}
    </Panel>
    {showVersion && <VersionModal close={() => setShowVersion(false)} done={async () => { setShowVersion(false); await versions.refresh() }} />}
  </div>
}

function SelectRun({ label, value, setValue, runs }: { label: string; value: number; setValue: (v: number) => void; runs: EvalRun[] }) {
  return <label className="field compact"><span>{label}</span><select value={value} onChange={(e) => setValue(Number(e.target.value))}><option value={0}>请选择</option>{runs.map((run) => <option value={run.id} key={run.id}>R{String(run.id).padStart(3, '0')} · 版本 #{run.prompt_version_id}</option>)}</select></label>
}

function CompareView({ data }: { data: CompareData }) {
  const metrics = data.metrics || data.metric_deltas || {}
  const entries = Object.entries(metrics)
  const base = data.baseline_metrics || {}
  const candidate = data.candidate_metrics || {}
  const paired = Array.from(new Set([...Object.keys(base), ...Object.keys(candidate)]))
  const rows = data.rows || data.regressions || []
  const regressions = data.severe_regressions ?? rows.filter((row) => row.severe_regression === true).length
  return <div className="compare-result">{paired.length ? <div className="metric-compare-table"><div className="metric-compare-head"><span>核心指标</span><b>基线</b><b>候选</b><b>变化</b></div>{paired.map((key) => { const before = base[key]; const after = candidate[key]; const delta = typeof before === 'number' && typeof after === 'number' ? after - before : null; const isRate = key.includes('rate'); return <div key={key}><span>{humanize(key)}</span><b>{isRate ? `${before ?? '—'}%` : fmtNum(before, key.includes('cost') ? 4 : 1)}</b><b>{isRate ? `${after ?? '—'}%` : fmtNum(after, key.includes('cost') ? 4 : 1)}</b><b className={delta === null ? '' : delta >= 0 ? 'delta-up' : 'delta-down'}>{delta === null ? '—' : `${delta > 0 ? '+' : ''}${fmtNum(delta, 1)}${isRate ? 'pp' : ''}`}</b></div>})}</div> : entries.length ? <div className="compare-metrics">{entries.map(([key, value]) => <div key={key}><span>{humanize(key)}</span><strong>{typeof value === 'number' ? (key.includes('rate') || key.includes('score') ? percent(value) : fmtNum(value, 2)) : String(value ?? '—')}</strong></div>)}</div> : <pre className="json-view">{JSON.stringify(data, null, 2)}</pre>}<div className={cn('regression-note', regressions === 0 && 'safe')}><Icon name={regressions === 0 ? 'check' : 'alert'} /><strong>{regressions}</strong> 条严重回归</div></div>
}

function VersionModal({ close, done }: { close: () => void; done: () => Promise<void> }) {
  const [form, setForm] = useState({ name: '', model: 'demo-rule-engine', system_prompt: '', temperature: 0.2, is_baseline: false })
  const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  async function submit(e: FormEvent) { e.preventDefault(); setBusy(true); setError(''); try { await api.createVersion(form); await done() } catch (err) { setError(getError(err)) } finally { setBusy(false) } }
  return <Modal title="新建 Prompt 版本" onClose={close}><form onSubmit={(e) => void submit(e)} className="form-grid"><label className="field"><span>版本名称</span><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="例如：v2 · 引用增强" /></label><label className="field"><span>模型标识</span><input required value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} /></label><label className="field full"><span>系统提示词</span><textarea required rows={7} value={form.system_prompt} onChange={(e) => setForm({ ...form, system_prompt: e.target.value })} placeholder="定义角色、回答边界、引用要求和失败兜底……" /></label><label className="field"><span>Temperature</span><input type="number" min="0" max="2" step="0.1" value={form.temperature} onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })} /></label><label className="check-field"><input type="checkbox" checked={form.is_baseline} onChange={(e) => setForm({ ...form, is_baseline: e.target.checked })} />设为基线版本</label>{error && <p className="field-error full"><Icon name="alert" size={15} />{error}</p>}<div className="modal-actions full"><button type="button" className="btn btn-secondary" onClick={close}>取消</button><button className="btn btn-primary" disabled={busy}>{busy && <Spinner />}保存版本</button></div></form></Modal>
}

function BadcasesPage() {
  const runs = useLoad<EvalRun[]>(api.runs, [])
  const [runId, setRunId] = useState(0)
  const badcases = useLoad<EvalResult[]>(() => runId ? api.badcases(runId) as Promise<EvalResult[]> : Promise.resolve([]), [runId])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const selected = badcases.data?.find((b) => b.id === selectedId) || badcases.data?.[0]
  useEffect(() => { if (badcases.data?.length && !badcases.data.some((b) => b.id === selectedId)) setSelectedId(badcases.data[0].id) }, [badcases.data, selectedId])
  return <div className="page-grid">
    <div className="page-heading"><div><span className="eyebrow">HUMAN IN THE LOOP</span><h1>Badcase 审核</h1><p>失败项与高风险项必须经过人工复核，模型评分不能替代发布责任。</p></div><label className="field run-picker"><span>评测运行</span><select value={runId} onChange={(e) => setRunId(Number(e.target.value))}><option value={0}>请选择运行</option>{runs.data?.map((r) => <option key={r.id} value={r.id}>R{String(r.id).padStart(3, '0')} · {r.status}</option>)}</select></label></div>
    {runs.error && <ErrorState message={runs.error} retry={() => void runs.refresh()} />}
    {!runId ? <Panel><EmptyState title="先选择一次评测运行" description="系统会呈现该运行中待审核或评分未达标的结果。" /></Panel> : badcases.loading ? <Panel><LoadingRows /></Panel> : badcases.error ? <ErrorState message={badcases.error} retry={() => void badcases.refresh()} /> : !badcases.data?.length ? <Panel><EmptyState title="没有待处理的 Badcase" description="此运行没有返回失败项或待人工复核项。" /></Panel> : <div className="review-layout"><Panel title={`问题队列 · ${badcases.data.length}`} subtitle="按严重程度与安全风险优先处理"><div className="badcase-list">{badcases.data.map((item) => { const severity = item.effective_severity ?? item.severity; return <button key={item.id} className={cn('badcase-item', selected?.id === item.id && 'active')} onClick={() => setSelectedId(item.id)}><div><Badge tone={severity === 'high' || severity === 'critical' || !item.safety_pass ? 'bad' : 'warn'}>{severity || (item.safety_pass ? '待确认' : '安全失败')}</Badge><StatusBadge status={item.review_status || 'pending_review'} /></div><strong>{item.external_id || `用例 #${item.case_id}`} · {item.case_title || ''}</strong><p>{item.effective_failure_category ?? item.failure_category ?? '未分类问题'}</p><small>正确性 {fmtNum(item.effective_correctness_score ?? item.correctness_score, 1)} · 依据 {fmtNum(item.effective_groundedness_score ?? item.groundedness_score, 1)}</small></button>})}</div></Panel>{selected && <ReviewDetail item={selected} onDone={() => void badcases.refresh()} />}</div>}
  </div>
}

function ReviewDetail({ item, onDone }: { item: EvalResult; onDone: () => void }) {
  const scores = (result: EvalResult) => ({ correctness_score: result.effective_correctness_score ?? result.correctness_score, groundedness_score: result.effective_groundedness_score ?? result.groundedness_score, task_completion_score: result.effective_task_completion_score ?? result.task_completion_score })
  const [form, setForm] = useState<HumanReview>({ decision: 'pass', ...scores(item), failure_category: item.effective_failure_category ?? item.failure_category ?? '', severity: item.effective_severity ?? item.severity ?? 'medium', notes: '' })
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState('')
  useEffect(() => setForm({ decision: 'pass', ...scores(item), failure_category: item.effective_failure_category ?? item.failure_category ?? '', severity: item.effective_severity ?? item.severity ?? 'medium', notes: '' }), [item])
  async function submit() { setBusy(true); setMessage(''); try { await api.review(item.id, form); setMessage('审核意见已保存。'); onDone() } catch (e) { setMessage(getError(e)) } finally { setBusy(false) } }
  return <Panel className="review-detail" title={`审核结果 #${item.id}`} subtitle={`运行 R${item.run_id} · 用例 #${item.case_id}`}>
    <div className="answer-block"><span>模型回答</span><p>{item.output_text || '无有效输出'}</p></div>
    <div className="score-strip">{[['正确性', item.effective_correctness_score ?? item.correctness_score], ['依据充分度', item.effective_groundedness_score ?? item.groundedness_score], ['任务完成', item.effective_task_completion_score ?? item.task_completion_score]].map(([label, score]) => <div key={String(label)}><span>{label}</span><strong>{fmtNum(score as number, 1)}</strong></div>)}<div><span>安全检查</span><strong className={item.safety_pass ? 'good-text' : 'bad-text'}>{item.safety_pass ? '通过' : '失败'}</strong></div></div>
    <div className="form-grid review-form"><label className="field"><span>审核决定</span><select value={form.decision} onChange={(e) => setForm({ ...form, decision: e.target.value })}><option value="pass">人工判定通过</option><option value="fail">人工判定失败</option></select></label><label className="field"><span>严重程度</span><select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}><option value="none">无</option><option value="low">低</option><option value="medium">中</option><option value="high">高</option><option value="critical">致命</option></select></label><label className="field"><span>失败分类</span><input value={form.failure_category} onChange={(e) => setForm({ ...form, failure_category: e.target.value })} /></label><label className="field"><span>正确性评分（0–100）</span><input type="number" min="0" max="100" step="1" value={form.correctness_score} onChange={(e) => setForm({ ...form, correctness_score: Number(e.target.value) })} /></label><label className="field"><span>依据充分度（0–100）</span><input type="number" min="0" max="100" step="1" value={form.groundedness_score} onChange={(e) => setForm({ ...form, groundedness_score: Number(e.target.value) })} /></label><label className="field"><span>任务完成度（0–100）</span><input type="number" min="0" max="100" step="1" value={form.task_completion_score} onChange={(e) => setForm({ ...form, task_completion_score: Number(e.target.value) })} /></label><label className="field full"><span>审核备注</span><textarea rows={3} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="记录判断依据、修正原因和后续建议" /></label></div>
    {message && <p className={message.includes('已保存') ? 'success-copy' : 'field-error'}>{message}</p>}<button className="btn btn-primary" disabled={busy} onClick={() => void submit()}>{busy && <Spinner />}提交人工审核</button>
  </Panel>
}

function ReleasePage() {
  const runs = useLoad<EvalRun[]>(api.runs, [])
  const complete = runs.data?.filter((r) => r.status === 'completed') || []
  const [baseline, setBaseline] = useState(0); const [candidate, setCandidate] = useState(0)
  const gate = useLoad<ReleaseGateData | null>(() => baseline && candidate ? api.gate(candidate, baseline) : Promise.resolve(null), [baseline, candidate])
  const [report, setReport] = useState<Record<string, unknown> | null>(null); const [reportError, setReportError] = useState(''); const [loadingReport, setLoadingReport] = useState(false)
  async function loadReport() { if (!candidate) return; setLoadingReport(true); setReportError(''); try { setReport(await api.report(candidate)) } catch (e) { setReportError(getError(e)) } finally { setLoadingReport(false) } }
  function download() { if (!report) return; const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `quality-report-run-${candidate}.json`; a.click(); URL.revokeObjectURL(url) }
  const passed = gate.data?.passed ?? gate.data?.decision === 'allow_release'
  const gateChecks = gate.data?.checks ? (Array.isArray(gate.data.checks) ? gate.data.checks : Object.entries(gate.data.checks).map(([name, check]) => ({ name, ...check }))) : []
  return <div className="page-grid">
    <div className="page-heading"><div><span className="eyebrow">RELEASE DECISION</span><h1>发布门禁</h1><p>将质量阈值转化为清晰、可解释、可导出的发布结论。</p></div></div>
    <Panel><div className="gate-selector"><SelectRun label="基线运行" value={baseline} setValue={setBaseline} runs={complete} /><span className="compare-arrow"><Icon name="arrow" /></span><SelectRun label="候选运行" value={candidate} setValue={setCandidate} runs={complete} /><button className="btn btn-dark" disabled={!candidate || loadingReport} onClick={() => void loadReport()}>{loadingReport ? <Spinner /> : <Icon name="download" />}生成报告</button></div></Panel>
    {!baseline || !candidate ? <Panel><EmptyState title="选择基线与候选运行" description="门禁只对已完成运行计算，不会用估算值或伪造数据填充。" /></Panel> : gate.loading ? <Panel><LoadingRows /></Panel> : gate.error ? <ErrorState message={gate.error} retry={() => void gate.refresh()} /> : gate.data && <div className="gate-layout"><section className={cn('decision-card', passed ? 'pass' : 'block-release')}><div className="decision-icon"><Icon name={passed ? 'check' : 'alert'} size={28} /></div><span>自动门禁结论</span><h2>{passed ? '允许发布' : '阻断发布'}</h2><p>{passed ? '候选版本满足全部默认质量阈值。仍建议确认人工审核已闭环。' : '候选版本存在未达标项。请先处理 Badcase，再重新评测。'}</p><div className="decision-meta"><span>基线 R{baseline}</span><Icon name="arrow" /><span>候选 R{candidate}</span></div></section><Panel title="门禁检查项" subtitle="默认阈值由项目验收标准固定">{gateChecks.length ? <div className="checks">{gateChecks.map((check, index) => { const threshold = check.threshold ?? check.minimum ?? check.maximum ?? check.limit ?? check.expected ?? '—'; return <div key={index}><span className={check.passed ? 'check-ok' : 'check-fail'}><Icon name={check.passed ? 'check' : 'close'} size={15} /></span><div><strong>{humanize(check.name || `检查项 ${index + 1}`)}</strong><p>实际 {String(check.actual ?? '—')} · 阈值 {String(threshold)}</p></div><StatusBadge status={check.passed ? 'approved' : 'rejected'} /></div> })}</div> : <pre className="json-view">{JSON.stringify(gate.data, null, 2)}</pre>}{gate.data.reasons?.map((r) => <p className="gate-reason" key={r}>{r}</p>)}</Panel></div>}
    {(report || reportError) && <Panel title="质量评测报告" subtitle={`候选运行 R${candidate}`} action={report && <button className="btn btn-secondary" onClick={download}><Icon name="download" />下载 JSON</button>}>{reportError ? <ErrorState message={reportError} retry={() => void loadReport()} /> : <pre className="json-view report-view">{JSON.stringify(report, null, 2)}</pre>}</Panel>}
  </div>
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => { const fn = (e: KeyboardEvent) => e.key === 'Escape' && onClose(); document.addEventListener('keydown', fn); return () => document.removeEventListener('keydown', fn) }, [onClose])
  return <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><section className="modal" role="dialog" aria-modal="true" aria-label={title}><header><h2>{title}</h2><button className="icon-btn" onClick={onClose} aria-label="关闭"><Icon name="close" /></button></header><div className="modal-body">{children}</div></section></div>
}

function humanize(value: string) {
  const map: Record<string, string> = { correctness_score: '正确性', correctness_avg: '平均正确性', groundedness_score: '依据充分度', groundedness_pass_rate: '依据通过率', task_completion_score: '任务完成', task_completion_pass_rate: '任务完成率', safety_pass_rate: '安全通过率', safety_failures: '安全失败', high_risk_safety_failures: '高风险安全失败', avg_latency_ms: '平均延迟', total_cost_cny: '总成本', total_tokens: 'Token 总量', severe_regressions: '严重回归', needs_review: '待人工审核', required_reviews: '待人工审核', run_completed: '运行完成' }
  return map[value] || value.replaceAll('_', ' ')
}

const categoryLabels: Record<string, string> = { operation: '操作咨询', troubleshooting: '故障排查', ambiguous: '歧义输入', out_of_scope: '越界问题', prompt_injection: '提示注入' }

export default function App() {
  const initial = (location.hash.replace('#/', '') || 'overview') as PageId
  const [page, setPage] = useState<PageId>(nav.some((v) => v.id === initial) ? initial : 'overview')
  const health = useLoad<Record<string, unknown>>(api.health, [])
  const [mobileNav, setMobileNav] = useState(false)
  function navigate(to: PageId) { location.hash = `/${to}`; setPage(to); setMobileNav(false); window.scrollTo(0, 0) }
  useEffect(() => { const fn = () => { const next = location.hash.replace('#/', '') as PageId; if (nav.some((v) => v.id === next)) setPage(next) }; window.addEventListener('hashchange', fn); return () => window.removeEventListener('hashchange', fn) }, [])
  return <div className="app-shell">
    <aside className={cn('sidebar', mobileNav && 'mobile-open')}>
      <div className="brand"><div className="brand-mark">A<span>Q</span></div><div><strong>Agent QualityOps</strong><small>智能体质量运营平台</small></div></div>
      <nav>{nav.map((item) => <button key={item.id} className={page === item.id ? 'active' : ''} onClick={() => navigate(item.id)}><Icon name={item.id} /><span><strong>{item.label}</strong><small>{item.hint}</small></span></button>)}</nav>
      <div className="sidebar-foot"><div className="service"><i className={health.error ? 'offline' : health.loading ? 'checking' : 'online'} /><div><strong>{health.error ? '服务未连接' : health.loading ? '正在检查' : '后端服务正常'}</strong><small>{health.error ? '数据不会被模拟' : 'FastAPI · SQLite'}</small></div><button onClick={() => void health.refresh()} aria-label="重新检测"><Icon name="refresh" size={14} /></button></div><p>Agent QualityOps <b>v0.1</b></p></div>
    </aside>
    <div className="main-wrap">
      <header className="topbar"><button className="menu-btn" onClick={() => setMobileNav(!mobileNav)} aria-label="菜单"><span /><span /><span /></button><div className="breadcrumbs"><span>质量运营台</span><b>/</b><strong>{titleFor(page)}</strong></div><div className="topbar-right"><span className="env">离线评测环境</span><span className="avatar">ZC</span></div></header>
      {health.error && <div className="offline-banner"><Icon name="alert" /><span><strong>后端服务未连接。</strong> 页面不会展示模拟成功数据；启动 FastAPI 后点击重试。</span><button onClick={() => void health.refresh()}>重新连接</button></div>}
      <main>{page === 'overview' && <OverviewPage navigate={navigate} />}{page === 'cases' && <CasesPage />}{page === 'runs' && <RunsPage />}{page === 'badcases' && <BadcasesPage />}{page === 'release' && <ReleasePage />}</main>
    </div>
    {mobileNav && <div className="nav-overlay" onClick={() => setMobileNav(false)} />}
  </div>
}
