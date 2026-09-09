import { commandTemplate, hash, id, recordApproval, snapshot, unchanged } from "./common.mjs"

// The host owns session creation, slash parsing, model selection and navigation.
// This controller only supplies one approved input to a mounted HOME prompt.
export function createHandoff(api, { home, now = Date.now } = {}) {
  let pending
  let homePrompt
  let sourcePrompt
  const consumed = new Set()
  const active = () => !api.lifecycle.signal.aborted
  const currentSource = () => api.route.current.name === "session" ? api.route.current.params?.sessionID : undefined
  const lastUser = (sessionID) => api.state.session.messages(sessionID).findLast((message) => message.role === "user")?.id
  const configHash = () => hash(JSON.stringify(api.state.config))

  function fitsDialog(message) {
    const width = Math.min(116, api.renderer.width - 2) - 4
    const height = Math.floor(api.renderer.height * 0.75) - 8
    if (width < 60 || height < 1) return false
    let rows = 0
    for (const line of message.split("\n")) {
      rows++
      let used = 0
      for (const token of line.match(/\S+|\s+/g) ?? []) {
        // UTF-8 bytes conservatively bound terminal columns without bundling
        // a renderer dependency. The built-in confirm dialog does not scroll.
        const columns = Buffer.byteLength(token)
        if (used && used + columns > width) { rows++; used = 0 }
        rows += Math.floor((columns - 1) / width)
        used = columns > width ? ((columns - 1) % width) + 1 : used + columns
      }
    }
    return rows <= height
  }

  function fail(error) {
    const wasApproval = pending?.phase === "approval"
    pending = undefined
    if (wasApproval) api.ui.dialog.clear()
    if (active()) api.ui.toast({ variant: "warning", message: `Fresh handoff stopped: ${error.message}. No automatic retry.` })
  }

  function guard(staged, visible = true, idle = false) {
    if (!active() || !api.state.ready) throw new Error("TUI is not active and ready")
    if (visible && currentSource() !== staged.sourceSessionID) throw new Error("Source is no longer visible")
    const source = api.state.session.get(staged.sourceSessionID)
    if (!source || source.parentID || source.workspaceID || source.permission?.length) {
      throw new Error("Only local root sessions without session-specific permission overrides are supported")
    }
    if (source.directory !== staged.directory || api.state.path.directory !== staged.directory) throw new Error("Source directory changed or differs from the native home destination")
    if (staged.configHash && staged.configHash !== configHash()) throw new Error("Configuration changed")
    if (staged.lastUserID && staged.lastUserID !== lastUser(staged.sourceSessionID)) throw new Error("Source received another user message")
    if (api.state.session.permission(staged.sourceSessionID).length || api.state.session.question(staged.sourceSessionID).length) throw new Error("Source has pending permission/question requests")
    if (idle && api.state.session.status(staged.sourceSessionID)?.type !== "idle") throw new Error("Source is no longer idle")
    if (staged.expires && now() > staged.expires) throw new Error("Preparation expired")
  }

  async function checkCommand(staged) {
    const [commands, agents] = await Promise.all([
      api.client.command.list({ directory: staged.directory }, { throwOnError: true }),
      api.client.app.agents({ directory: staged.directory }, { throwOnError: true }),
    ])
    const command = commands.data?.find((item) => item.name === "implement-plan")
    if (!command || command.template.trim() !== commandTemplate || command.agent !== "build" || command.model || command.subtask !== false) {
      throw new Error("The dotfiles implement-plan command is missing or overridden")
    }
    const build = agents.data?.find((item) => item.name === "build")
    if (!build || build.mode === "subagent" || build.hidden || build.model || build.variant) {
      throw new Error("Build must be a visible primary agent without model/variant overrides to preserve the native selection")
    }
  }

  function confirm(staged) {
    if (pending !== staged || staged.phase !== "approval") return
    staged.phase = "approved"
    // DialogConfirm clears its stack AFTER invoking onConfirm. Continue after
    // that callback, rather than mounting a home prompt underneath the dialog.
    queueMicrotask(() => {
      try {
        if (pending !== staged) return
        guard(staged, true, true)
        if (api.ui.dialog.open) throw new Error("Another dialog is open")
        if (!fitsDialog(staged.message)) throw new Error("Terminal became too small for the approval text")
        if (!sourcePrompt || sourcePrompt.current.input || sourcePrompt.current.parts.length) throw new Error("Source prompt is missing or has an unsent draft")
        Object.assign(staged, recordApproval(staged, home))
        staged.phase = "home"
        staged.homeDeadline = now() + 3000
        api.route.navigate("home")
        if (api.route.current.name !== "home") throw new Error("Native home navigation failed")
      } catch (error) {
        fail(error)
      }
    })
  }

  async function tick() {
    const staged = pending
    if (!staged) return
    try {
      guard(staged, staged.phase !== "home", staged.phase === "home")
      if (staged.phase === "home") {
        if (api.route.current.name !== "home") throw new Error("Home is no longer visible")
        if (now() > staged.homeDeadline) throw new Error("Native home prompt did not become available")
        const prompt = homePrompt
        if (!prompt || !prompt.focused || api.ui.dialog.open) return
        if (prompt.current.input || prompt.current.parts.length) throw new Error("Home contains an unsent draft; it was not overwritten")
        unchanged(staged, home)
        const input = `/implement-plan ${staged.planPath}`
        // Consume BEFORE invoking native UI code. Ref callbacks, events, failed
        // submissions and duplicate idle events must never cause a second send.
        pending = undefined
        prompt.set({ input, parts: [] })
        if (!active() || api.route.current.name !== "home" || homePrompt !== prompt || prompt.current.input !== input || prompt.current.parts.length) throw new Error("Native prompt changed before submission")
        prompt.submit()
        return
      }
      if (staged.phase !== "waiting" || !staged.completed || api.state.session.status(staged.sourceSessionID)?.type !== "idle" || api.ui.dialog.open) return
      staged.phase = "checking"
      await checkCommand(staged)
      if (pending !== staged) return
      guard(staged, true, true)
      unchanged(staged, home)
      if (api.ui.dialog.open) throw new Error("Another dialog opened")
      if (!sourcePrompt || sourcePrompt.current.input || sourcePrompt.current.parts.length) throw new Error("Source prompt is missing or has an unsent draft")
      const message = `${staged.planPath}\nSHA-256: ${staged.planHash}\nDirectory: ${staged.directory}\n\n${staged.effects}\n\nConfirm approves these exact plan bytes and starts /implement-plan in a NEW root session using the native home prompt. Build replaces Plan restrictions; configured Build tool permissions and the current TUI permission mode apply. Keep the native selected model/variant. No transcript, fork, compaction, or session permission grants are copied. The old session remains. Cancel starts nothing.`
      if (!fitsDialog(message)) throw new Error("Approval text does not fit this terminal; enlarge it or shorten the effects summary before preparing again")
      staged.message = message
      staged.phase = "approval"
      api.ui.dialog.replace(() => api.ui.DialogConfirm({
        title: "Approve Exact Plan And Start Fresh Implementation?",
        message,
        onConfirm: () => confirm(staged),
        onCancel: () => { if (pending === staged) pending = undefined },
      }), () => { if (pending === staged && staged.phase === "approval") pending = undefined })
      api.ui.dialog.setSize("xlarge")
    } catch (error) {
      if (pending === staged || !pending) fail(error)
    }
  }

  return {
    handle(message) {
      if (message.type === "probe") return { available: active() && api.state.ready && currentSource() === message.sourceSessionID && api.state.path.directory === message.directory }
      if (message.type !== "prepare") throw new Error("Unknown handoff request")
      if (pending || consumed.has(message.sourceMessageID)) throw new Error("Duplicate handoff; this source turn was already prepared")
      guard(message)
      if (typeof message.effects !== "string" || !message.effects.trim() || message.effects.length > 4000 || /[\x00-\x09\x0b-\x1f\x7f]/.test(message.effects)) throw new Error("Invalid material effects summary")
      if (!api.state.session.messages(message.sourceSessionID).some((item) => item.id === message.sourceMessageID && item.role === "assistant")) throw new Error("Preparation does not belong to the visible source turn")
      const plan = snapshot(message.planPath, home)
      if (plan.planHash !== message.planHash || plan.progressHash !== message.progressHash) throw new Error("Local plan/progress differs from preparation")
      const lastUserID = lastUser(message.sourceSessionID)
      if (!lastUserID) throw new Error("Source user turn is unavailable")
      const staged = { ...plan, id: id(), sourceSessionID: message.sourceSessionID, sourceMessageID: message.sourceMessageID, directory: message.directory, effects: message.effects, lastUserID, configHash: configHash(), expires: now() + 10 * 60_000, phase: "waiting", completed: false }
      consumed.add(message.sourceMessageID)
      pending = staged
      return { id: staged.id }
    },
    part(event) {
      const part = event.properties.part
      if (!pending || part.sessionID !== pending.sourceSessionID || part.messageID !== pending.sourceMessageID || part.type !== "tool" || part.tool !== "prepare_plan_handoff") return
      if (part.state.status === "completed" && part.state.metadata?.handoffID === pending.id) pending.completed = true
    },
    bindHome(ref) { homePrompt = ref; return pending?.phase === "home" },
    bindSource(ref) { sourcePrompt = ref },
    tick,
    dispose() { pending = undefined; homePrompt = undefined; sourcePrompt = undefined },
  }
}
