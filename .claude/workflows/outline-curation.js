export const meta = {
  name: 'outline-curation',
  description: '大綱正本：結構提議 judge panel 與可答性判者 fan-out（schema 強制、判者隔離）',
  phases: [{ title: 'Structure' }, { title: 'Answerability' }, { title: 'Reconcile' }],
}

// args = {step: 'structure'|'answerability', cells, fineIdEnum, frozenAt, rubricSha, inputsSha, ...}
// ⛔ 禁用內建目前時間／亂數 API（會破壞續跑快取）——時間戳一律由 args.frozenAt 傳入。

if (args.step === 'structure') {
  throw new Error('structure: 2.3 實作')
}

if (args.step !== 'answerability') {
  throw new Error(`未知 step：${args.step}（須為 'structure' 或 'answerability'）`)
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['cell_id', 'label', 'fine_id', 'evidence_unit', 'confidence', 'provisional'],
  properties: {
    cell_id: { type: 'string' },
    label: { type: 'string', enum: ['answerable', 'partial', 'no_source', 'deliberate_no'] },
    fine_id: { type: ['string', 'null'], enum: [...args.fineIdEnum, null] },
    evidence_unit: { type: ['integer', 'null'] },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    provisional: { type: 'boolean', enum: [true] },
  },
}

phase('Answerability')

// 判者互不可見：每個 agent() 只拿 c.judgePrompt，⛔ 不把 v1 傳給 judge2、不把 v1/v2 傳給 judge3。
const results = await pipeline(
  args.cells,
  c => agent(c.judgePrompt, { phase: 'Answerability', label: `judge1:${c.cellId}`, effort: 'low', schema: VERDICT_SCHEMA }),
  (v1, c) => agent(c.judgePrompt, { phase: 'Answerability', label: `judge2:${c.cellId}`, effort: 'low', schema: VERDICT_SCHEMA })
    .then(v2 => ({ c, v1, v2 })),
  r => (r.v1 && r.v2 && r.v1.label === r.v2.label)
    ? r
    : agent(r.c.judgePrompt, { phase: 'Answerability', label: `judge3:${r.c.cellId}`, effort: 'low', schema: VERDICT_SCHEMA })
      .then(v3 => ({ ...r, v3 })),
)

phase('Reconcile')

let agree = 0
let agentsUsed = 0
let droppedCells = 0
const labels = []

for (const r of results) {
  if (!r) {
    droppedCells++
    continue
  }
  const { c, v1, v2, v3 } = r
  const verdicts = [v1, v2, v3].filter(Boolean)
  agentsUsed += verdicts.length

  if (!v1 || !v2) {
    droppedCells++
    log(`${c.cellId} skipped（判者結果缺失，no silent caps）`)
    continue
  }

  const isAgree = v1.label === v2.label
  if (isAgree) agree++

  let finalLabel
  let unresolved
  if (isAgree) {
    finalLabel = v1.label
  } else if (v3 && (v3.label === v1.label || v3.label === v2.label)) {
    finalLabel = v3.label
  } else {
    finalLabel = 'no_source'
    unresolved = true
  }

  const winner = verdicts.find(v => v.label === finalLabel) || v1
  const entry = {
    cell_id: c.cellId,
    label: finalLabel,
    fine_id: winner.fine_id,
    evidence_unit: winner.evidence_unit,
    confidence: winner.confidence,
    provisional: true,
    verdicts,
  }
  if (unresolved) entry.unresolved = true
  labels.push(entry)
  log(`${c.cellId} ${finalLabel}`)
}

if (droppedCells > 0) {
  log(`${droppedCells} 格因判者結果缺失被跳過（no silent caps）`)
}

const total = labels.length
const agreementRate = total > 0 ? agree / total : 0
const needs_rubric_revision = agreementRate < 0.90

return {
  step: 'answerability',
  frozenAt: args.frozenAt,
  rubricSha: args.rubricSha,
  inputsSha: args.inputsSha,
  total,
  agree,
  agreementRate,
  needs_rubric_revision,
  agentsUsed,
  labels,
}
