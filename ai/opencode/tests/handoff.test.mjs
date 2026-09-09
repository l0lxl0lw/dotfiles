import assert from "node:assert/strict"
import { mkdtempSync, mkdirSync, readFileSync, realpathSync, rmSync, symlinkSync, writeFileSync } from "node:fs"
import { homedir, tmpdir } from "node:os"
import path from "node:path"
import { test } from "node:test"
import { commandTemplate, snapshot } from "../handoff/common.mjs"
import { createHandoff } from "../handoff/native.mjs"
import { listenLocal, prepareLocal } from "../handoff/transport.mjs"
import plugin from "../handoff/tui.mjs"

function fixture(t) {
  const home = realpathSync(mkdtempSync(path.join(tmpdir(), "handoff-test-")))
  t.after(() => rmSync(home, { recursive: true, force: true }))
  const directory = path.join(home, "repo")
  const planPath = path.join(home, ".agents/plans/project/task with spaces/plan.md")
  mkdirSync(path.dirname(planPath), { recursive: true })
  mkdirSync(directory)
  writeFileSync(planPath, "# Exact approved plan\n\nAC-01: change only the fixture.\n")
  const progressPath = path.join(path.dirname(planPath), "progress.md")
  const source = { id: "source", directory }
  const messages = [{ id: "user-1", role: "user" }, { id: "assistant-1", role: "assistant" }]
  const controller = new AbortController()
  const calls = []
  let status = "busy"
  let time = 0
  let dialog
  let onClose
  const api = {
    app: { version: "1.18.30" },
    renderer: { width: 140, height: 60 },
    lifecycle: { signal: controller.signal },
    state: {
      ready: true,
      config: { permission: { bash: "ask" } },
      path: { directory },
      session: {
        get: () => source,
        messages: () => messages,
        status: () => ({ type: status }),
        permission: () => [],
        question: () => [],
      },
    },
    route: {
      current: { name: "session", params: { sessionID: source.id } },
      navigate(name) { calls.push(["navigate", name]); api.route.current = { name } },
    },
    client: {
      command: { list: async () => ({ data: [{ name: "implement-plan", template: commandTemplate, agent: "build", subtask: false }] }) },
      app: { agents: async () => ({ data: [{ name: "build", mode: "primary" }] }) },
      session: new Proxy({}, { get() { throw new Error("Controller must NEVER call a session API") } }),
    },
    ui: {
      toast(value) { calls.push(["toast", value.message]) },
      DialogConfirm(props) { dialog = props; return props },
      dialog: {
        open: false,
        replace(render, close) { calls.push(["popup"]); api.ui.dialog.open = true; onClose = close; render() },
        clear() { api.ui.dialog.open = false; onClose?.() },
        setSize() {},
      },
    },
  }
  const handoff = createHandoff(api, { home, now: () => time })
  const prompt = {
    focused: true,
    current: { input: "", parts: [] },
    set(value) { calls.push(["set", value]); this.current = value },
    submit() { calls.push(["submit", this.current.input]) },
  }
  handoff.bindSource({ current: { input: "", parts: [] } })
  const request = () => ({ type: "prepare", ...snapshot(planPath, home), effects: "Edit fixture only; run mocked tests; no network or git writes.", sourceSessionID: source.id, sourceMessageID: "assistant-1", directory })
  function prepare() {
    const result = handoff.handle(request())
    handoff.part({ properties: { part: { sessionID: source.id, messageID: "assistant-1", type: "tool", tool: "prepare_plan_handoff", state: { status: "completed", metadata: { handoffID: result.id } } } } })
    return result
  }
  async function popup() { prepare(); status = "idle"; await handoff.tick() }
  async function confirm() { dialog.onConfirm(); api.ui.dialog.clear(); await Promise.resolve() }
  return { api, home, directory, source, messages, planPath, progressPath, calls, handoff, prompt, request, prepare, popup, confirm, controller, dialog: () => dialog, idle: () => { status = "idle" }, advance: (value) => { time += value } }
}

test("one approval then HOME native slash submission, no session APIs or copied context", async (t) => {
  const f = fixture(t)
  const original = "# Existing progress\nUnrelated evidence stays.\n"
  writeFileSync(f.progressPath, original)
  const planBefore = readFileSync(f.planPath)
  await f.popup()
  assert.match(f.dialog().message, /SHA-256: [a-f0-9]{64}/)
  assert.match(f.dialog().message, /Build replaces Plan restrictions/)
  assert.match(f.dialog().message, /Edit fixture only/)
  assert.equal(f.calls.filter(([name]) => name === "navigate").length, 0)
  await f.confirm()
  assert.equal(f.api.route.current.name, "home")
  f.handoff.bindHome(f.prompt)
  await f.handoff.tick()
  await f.handoff.tick()
  f.dialog().onConfirm()
  assert.deepEqual(f.calls.filter(([name]) => name !== "toast"), [
    ["popup"], ["navigate", "home"],
    ["set", { input: `/implement-plan ${f.planPath}`, parts: [] }],
    ["submit", `/implement-plan ${f.planPath}`],
  ])
  assert.deepEqual(readFileSync(f.planPath), planBefore)
  const progress = readFileSync(f.progressPath, "utf8")
  assert.ok(progress.startsWith(original))
  assert.match(progress, /user-approved-plan-and-fresh-implementation/)
  assert.match(progress, /DialogConfirm onConfirm/)
  assert.match(progress, /sourceSessionID.*source/)
  assert.match(progress, new RegExp(snapshot(f.planPath, f.home).planHash))
  assert.match(progress, /not evidence that submission or implementation succeeded/)
  assert.throws(() => f.handoff.handle(f.request()), /Duplicate/)
})

test("preparation returns before idle; completion metadata is also required", async (t) => {
  const f = fixture(t)
  f.handoff.handle(f.request())
  await f.handoff.tick()
  f.idle()
  await f.handoff.tick()
  assert.deepEqual(f.calls, [])
})

test("busy source never opens popup even after tool completion", async (t) => {
  const f = fixture(t)
  f.prepare()
  await f.handoff.tick()
  assert.deepEqual(f.calls, [])
  f.idle()
  await Promise.all([f.handoff.tick(), f.handoff.tick(), f.handoff.tick()])
  assert.equal(f.calls.filter(([name]) => name === "popup").length, 1)
})

for (const action of ["cancel", "escape", "dispose"]) {
  test(`${action} starts nothing and records no approval`, async (t) => {
    const f = fixture(t)
    await f.popup()
    if (action === "cancel") f.dialog().onCancel()
    if (action === "dispose") { f.controller.abort(); f.handoff.dispose() }
    f.api.ui.dialog.clear()
    f.dialog().onConfirm()
    await f.handoff.tick()
    assert.equal(f.calls.filter(([name]) => name === "navigate" || name === "submit").length, 0)
    assert.throws(() => readFileSync(f.progressPath), { code: "ENOENT" })
  })
}

for (const when of ["before popup", "during popup", "after approval"]) {
  for (const file of ["planPath", "progressPath"]) {
    test(`changed ${file} ${when} prevents native submission`, async (t) => {
      const f = fixture(t)
      if (when === "before popup") { f.prepare(); f.idle() }
      else await f.popup()
      if (when === "after approval") await f.confirm()
      writeFileSync(f[file], "Changed content")
      if (when === "during popup") await f.confirm()
      f.handoff.bindHome(f.prompt)
      await f.handoff.tick()
      assert.equal(f.calls.filter(([name]) => name === "submit").length, 0)
      assert.ok(f.calls.some(([name, message]) => name === "toast" && /changed/.test(message)))
    })
  }
}

for (const change of ["route", "user", "directory", "busy", "config"]) {
  test(`stale source (${change}) cannot confirm`, async (t) => {
    const f = fixture(t)
    await f.popup()
    if (change === "route") f.api.route.current = { name: "session", params: { sessionID: "other" } }
    if (change === "user") f.messages.push({ role: "user", id: "user-2" })
    if (change === "directory") f.api.state.path.directory = "/other"
    if (change === "busy") f.api.state.session.status = () => ({ type: "busy" })
    if (change === "config") f.api.state.config = {}
    await f.confirm()
    assert.equal(f.calls.filter(([name]) => name === "navigate").length, 0)
    assert.throws(() => readFileSync(f.progressPath), { code: "ENOENT" })
  })
}

for (const failure of ["navigate", "missing prompt", "draft", "navigate away", "expired", "throw submit"]) {
  test(`native ${failure} fails without retry or alternate session submission`, async (t) => {
    const f = fixture(t)
    await f.popup()
    if (failure === "navigate") f.api.route.navigate = () => {}
    await f.confirm()
    if (failure === "navigate away") f.api.route.current = { name: "session", params: { sessionID: "other" } }
    if (failure === "draft") f.prompt.current = { input: "my unsent draft", parts: [] }
    if (failure === "expired" || failure === "missing prompt") f.advance(4000)
    if (failure === "throw submit") f.prompt.submit = () => { f.calls.push(["attempt"]); throw new Error("native failure") }
    if (failure !== "missing prompt") f.handoff.bindHome(f.prompt)
    await f.handoff.tick()
    await f.handoff.tick()
    assert.equal(f.calls.filter(([name]) => name === "submit").length, 0)
    assert.equal(f.calls.filter(([name]) => name === "attempt").length, failure === "throw submit" ? 1 : 0)
    if (failure === "draft") assert.equal(f.prompt.current.input, "my unsent draft")
  })
}

for (const override of ["command", "build model", "build variant", "subagent", "workspace", "permission"]) {
  test(`reject unsupported ${override} without silently changing semantics`, async (t) => {
    const f = fixture(t)
    if (override === "command") f.api.client.command.list = async () => ({ data: [] })
    if (override === "build model") f.api.client.app.agents = async () => ({ data: [{ name: "build", mode: "primary", model: { providerID: "other", modelID: "other" } }] })
    if (override === "build variant") f.api.client.app.agents = async () => ({ data: [{ name: "build", mode: "primary", variant: "high" }] })
    if (override === "subagent") f.source.parentID = "parent"
    if (override === "workspace") f.source.workspaceID = "remote"
    if (override === "permission") f.source.permission = [{ permission: "edit", pattern: "*", action: "allow" }]
    if (["subagent", "workspace", "permission"].includes(override)) assert.throws(() => f.prepare(), /Only local root/)
    else await f.popup()
    assert.equal(f.calls.filter(([name]) => name === "popup" || name === "navigate").length, 0)
  })
}

test("no UI connection means no preparation; duplicate visible clients are rejected", async (t) => {
  const f = fixture(t)
  const request = { ...f.request(), sourceSessionID: `fixture-${f.home}` }
  await assert.rejects(prepareLocal(request), /No active local/)
  const handler = (message) => message.type === "probe" ? { available: message.sourceSessionID === request.sourceSessionID } : { id: "prepared" }
  const close1 = await listenLocal(handler)
  t.after(close1)
  assert.deepEqual(await prepareLocal(request), { id: "prepared" })
  const close2 = await listenLocal(handler)
  await assert.rejects(prepareLocal(request), /multiple local TUIs/)
  await close2()
})

test("plan and progress symlinks are rejected", (t) => {
  const f = fixture(t)
  const foreign = path.join(f.home, "foreign")
  writeFileSync(foreign, "do not modify")
  symlinkSync(foreign, f.progressPath)
  assert.throws(() => f.prepare())
  rmSync(f.progressPath)
  rmSync(f.planPath)
  symlinkSync(foreign, f.planPath)
  assert.throws(() => f.prepare(), /Symlinked/)
  assert.equal(readFileSync(foreign, "utf8"), "do not modify")
})

test("template syntax in paths cannot turn slash arguments into shell commands or attachments", (t) => {
  const f = fixture(t)
  for (const task of ["!`touch PWNED`", "@secret", "task\n/new", "task$1"]) {
    const planPath = path.join(f.home, ".agents/plans/project", task, "plan.md")
    assert.throws(() => snapshot(planPath, f.home), /absolute plan path|plain ASCII/)
  }
})

test("handoff home ref is not forwarded to the host CLI --prompt auto-submit hook", async (t) => {
  const f = fixture(t)
  assert.equal(f.handoff.bindHome(undefined), false)
  await f.popup()
  await f.confirm()
  assert.equal(f.handoff.bindHome(f.prompt), true)
  await f.handoff.tick()
  assert.equal(f.handoff.bindHome(undefined), false)
})

test("source drafts are preserved, not carried into the new session", async (t) => {
  const f = fixture(t)
  f.handoff.bindSource({ current: { input: "my unsent draft", parts: [] } })
  await f.popup()
  assert.equal(f.calls.filter(([name]) => name === "popup" || name === "navigate").length, 0)
  assert.ok(f.calls.some(([name, message]) => name === "toast" && /unsent draft/.test(message)))
})

test("approval text must fit the non-scrolling native dialog", async (t) => {
  const f = fixture(t)
  f.api.renderer = { width: 80, height: 15 }
  await f.popup()
  assert.equal(f.calls.filter(([name]) => name === "popup").length, 0)
  assert.ok(f.calls.some(([name, message]) => name === "toast" && /does not fit/.test(message)))
})

test("shrinking the terminal invalidates confirmation before approval recording", async (t) => {
  const f = fixture(t)
  await f.popup()
  f.api.renderer.height = 10
  await f.confirm()
  assert.equal(f.calls.filter(([name]) => name === "navigate").length, 0)
  assert.throws(() => readFileSync(f.progressPath), { code: "ENOENT" })
})

test("late command preflight cannot revive a disposed handoff", async (t) => {
  const f = fixture(t)
  let resolve
  f.api.client.command.list = () => new Promise((done) => { resolve = done })
  f.prepare()
  f.idle()
  const checking = f.handoff.tick()
  f.controller.abort()
  f.handoff.dispose()
  resolve({ data: [{ name: "implement-plan", template: commandTemplate, agent: "build", subtask: false }] })
  await checking
  assert.deepEqual(f.calls, [])
})

test("actual server plugin stages over local IPC and returns without approval", { skip: typeof Bun === "undefined" }, async (t) => {
  const f = fixture(t)
  const close = await listenLocal(f.handoff.handle)
  t.after(close)
  // Bun caches homedir at process startup, so isolate HOME in a child rather
  // than mutating the test runner's environment or touching the real plans dir.
  const script = `
    const { default: server } = await import(${JSON.stringify(new URL("../plugins/fresh-session.js", import.meta.url).href)});
    const hooks = await server();
    let metadata;
    const result = await hooks.tool.prepare_plan_handoff.execute(${JSON.stringify({ planPath: f.planPath, effects: "Fixture only; no implementation." })}, {
      sessionID: "source", messageID: "assistant-1", directory: ${JSON.stringify(f.directory)},
      abort: new AbortController().signal,
      metadata(value) { metadata = value.metadata },
      ask() { throw new Error("Preparation must not open a permission approval") },
    });
    console.log(JSON.stringify({ result, metadata }));
  `
  const child = Bun.spawn([process.execPath, "--eval", script], {
    env: { ...process.env, HOME: f.home, XDG_CONFIG_HOME: process.env.XDG_CONFIG_HOME || path.join(homedir(), ".config") },
    stdout: "pipe", stderr: "pipe",
  })
  const [output, error, code] = await Promise.all([new Response(child.stdout).text(), new Response(child.stderr).text(), child.exited])
  assert.equal(code, 0, error)
  const { result, metadata } = JSON.parse(output)
  assert.match(result, /No approval yet. STOP now/)
  assert.ok(result.includes(metadata.handoffID))
  assert.deepEqual(f.calls, [])
  assert.throws(() => readFileSync(f.progressPath), { code: "ENOENT" })
})

test("tracked command exactly matches the preflight contract", () => {
  const command = readFileSync(new URL("../commands/implement-plan.md", import.meta.url), "utf8")
  assert.equal(command.split("---")[2].trim(), commandTemplate)
  assert.match(command, /agent: build\nsubtask: false/)
})

test("actual TUI module initializes/disposes headlessly without any session effects", async () => {
  const controller = new AbortController()
  const disposers = []
  const slots = []
  const api = {
    app: { version: "1.18.30" },
    lifecycle: { signal: controller.signal, onDispose: (fn) => disposers.push(fn) },
    slots: { register: (value) => slots.push(value) },
    event: { on: () => {} },
    ui: { Prompt: (props) => props, Slot: (props) => props },
  }
  await plugin.tui(api)
  assert.deepEqual(Object.keys(slots[0].slots), ["home_prompt", "session_prompt"])
  const refs = []
  const home = slots[0].slots.home_prompt({}, { ref: (ref) => refs.push(ref) })
  home.ref("native-home-ref")
  const value = { session_id: "source", visible: true, disabled: false, ref: (ref) => refs.push(ref) }
  const source = slots[0].slots.session_prompt({}, value)
  source.ref("native-source-ref")
  value.disabled = true
  assert.equal(source.disabled, true)
  assert.deepEqual(refs, ["native-home-ref", "native-source-ref"])
  controller.abort()
  for (const dispose of disposers.reverse()) await dispose()
  await assert.rejects(plugin.tui({ ...api, app: { version: "1.18.31" } }), /verified only/)
})
