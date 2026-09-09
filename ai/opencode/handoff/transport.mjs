import { createConnection, createServer } from "node:net"
import { readdirSync } from "node:fs"
import path from "node:path"
import { id, socketDirectory } from "./common.mjs"

export function request(socketPath, message, signal) {
  return new Promise((resolve, reject) => {
    const socket = createConnection({ path: socketPath, signal })
    let input = ""
    socket.setTimeout(2000, () => socket.destroy(new Error("Local TUI did not respond")))
    socket.on("error", reject)
    socket.on("connect", () => socket.write(JSON.stringify(message) + "\n"))
    socket.on("data", (chunk) => {
      input += chunk
      if (input.length > 16384) return socket.destroy(new Error("Oversized handoff response"))
      if (!input.includes("\n")) return
      try {
        const result = JSON.parse(input.split("\n")[0])
        if (result.error) reject(new Error(result.error))
        else resolve(result)
      } catch (error) {
        reject(error)
      }
      socket.end()
    })
    socket.on("end", () => { if (!input.includes("\n")) reject(new Error("Local TUI disconnected")) })
  })
}

export async function prepareLocal(message, signal) {
  const directory = socketDirectory()
  const candidates = readdirSync(directory).filter((name) => name.endsWith(".sock"))
  if (candidates.length > 64) throw new Error("Too many handoff sockets; clean up stale sockets manually")
  const matches = (await Promise.all(candidates.map(async (name) => {
    const socket = path.join(directory, name)
    const result = await request(socket, { type: "probe", sourceSessionID: message.sourceSessionID, directory: message.directory }, signal).catch(() => undefined)
    return result?.available ? socket : undefined
  }))).filter(Boolean)
  if (matches.length !== 1) throw new Error(matches.length ? "Source is visible in multiple local TUIs; close the extra view first" : "No active local handoff TUI for this source; use the manual approval/fresh-session workflow")
  return request(matches[0], { ...message, type: "prepare" }, signal)
}

export async function listenLocal(handle) {
  const socketPath = path.join(socketDirectory(), `${process.pid}-${id()}.sock`)
  const clients = new Set()
  const server = createServer((socket) => {
    clients.add(socket)
    socket.on("close", () => clients.delete(socket))
    socket.on("error", () => {})
    socket.setTimeout(2000, () => socket.destroy())
    let input = ""
    let handled = false
    socket.on("data", (chunk) => {
      if (handled) return
      input += chunk
      if (input.length > 16384) return socket.destroy()
      if (!input.includes("\n")) return
      handled = true
      Promise.resolve().then(() => handle(JSON.parse(input.split("\n")[0])))
        .then((result) => socket.end(JSON.stringify(result) + "\n"))
        .catch((error) => socket.end(JSON.stringify({ error: error.message }) + "\n"))
    })
  })
  await new Promise((resolve, reject) => {
    server.once("error", reject)
    server.listen(socketPath, resolve)
  })
  return () => new Promise((resolve) => {
    for (const socket of clients) socket.destroy()
    server.close(resolve)
  })
}
