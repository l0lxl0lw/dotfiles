// OpenCode v1 plugin: preserve exposed messages, without calling a model.
import { spawn } from "node:child_process"
import { readFile } from "node:fs/promises"
import { homedir } from "node:os"
import { join } from "node:path"

export default async ({ client, directory }) => {
  const configPath = process.env.LIFE_MEMORY_CONFIG || join(homedir(), ".config/life-memory/config.json")
  const cfg = JSON.parse(await readFile(configPath, "utf8"))
  if (!cfg.enabled || process.env.LIFE_MEMORY_DISABLED === "1") return {}
  const run = (args, input) => new Promise((resolve, reject) => {
    const p = spawn(cfg.python, [cfg.runtime, ...args], { env: process.env, stdio: ["pipe", "pipe", "pipe"] })
    let out = "", err = ""
    p.stdout.on("data", b => { out += b })
    p.stderr.on("data", b => { err += b })
    p.on("error", reject)
    p.stdin.on("error", reject)
    p.on("close", code => code === 0 ? resolve(out) : reject(new Error(err)))
    p.stdin.end(input ? JSON.stringify(input) : "")
  })
  const chains = new Map()
  async function capture(id) {
    const response = await client.session.messages({ path: { id }, query: { directory } })
    if (response.error || !Array.isArray(response.data)) throw new Error("Life memory: session.messages failed")
    await run(["capture", "opencode"], { session_id: id, cwd: directory, messages: response.data })
  }
  return {
    "experimental.chat.system.transform": async (input, output) => {
      // User message metadata events may precede text-part persistence. Capture
      // again before inference so the current source is available for checkpointing.
      if (input.sessionID) await capture(input.sessionID)
      output.system.push(await run(input.sessionID ? ["brief", "opencode", input.sessionID] : ["brief"]))
    },
    "experimental.session.compacting": async (input, output) => {
      await capture(input.sessionID)
      output.context.push("Preserve the Life memory checkpoint obligation, vault path, and source links. Follow the life-memory skill before ending substantive work.")
    },
    event: async ({ event }) => {
      const info = event.properties?.info
      const id = event.properties?.sessionID || info?.sessionID
      const ready = event.type === "session.idle" ||
        (event.type === "message.updated" && (info?.role === "user" || info?.time?.completed))
      if (!ready || !id) return
      // Serialize per-session fetches so an older snapshot can't win a race.
      const next = (chains.get(id) || Promise.resolve()).then(() => capture(id)).catch(async error => {
        await client.app.log({ body: { service: "life-memory", level: "error", message: String(error) } })
      })
      chains.set(id, next)
      await next
      if (chains.get(id) === next) chains.delete(id)
    },
  }
}
