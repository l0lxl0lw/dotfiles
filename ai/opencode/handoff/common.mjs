import { createHash, randomUUID } from "node:crypto"
import { appendFileSync, constants, closeSync, fstatSync, lstatSync, mkdirSync, openSync, readFileSync, realpathSync } from "node:fs"
import { homedir } from "node:os"
import path from "node:path"

export const commandTemplate = "Read and follow the implement-plan skill for this explicitly approved plan:\n$ARGUMENTS\nDo not reconstruct the brainstorming transcript. Verify the plan hash and approval in adjacent progress.md before implementing."
export const hash = (bytes) => createHash("sha256").update(bytes).digest("hex")
export const id = () => randomUUID()

export function socketDirectory() {
  if (!process.getuid) throw new Error("Fresh handoff requires a local Unix TUI")
  // Short enough for Darwin's sockaddr_un, private to this OS user. A Unix
  // socket connection proves co-location; a matching remote path does not.
  const directory = `/tmp/opencode-handoff-${process.getuid()}`
  mkdirSync(directory, { mode: 0o700, recursive: true })
  const stat = lstatSync(directory)
  if (!stat.isDirectory() || stat.uid !== process.getuid() || (stat.mode & 0o077)) {
    throw new Error("Unsafe handoff socket directory")
  }
  return directory
}

function readRegular(file, optional = false) {
  let fd
  try {
    fd = openSync(file, constants.O_RDONLY | constants.O_NOFOLLOW)
    const stat = fstatSync(fd)
    if (!stat.isFile() || stat.size > 512 * 1024 || stat.nlink !== 1) throw new Error("Expected a small, unlinked regular plan/progress file")
    return readFileSync(fd)
  } catch (error) {
    if (optional && error.code === "ENOENT") return undefined
    throw error
  } finally {
    if (fd !== undefined) closeSync(fd)
  }
}

export function snapshot(planPath, home = homedir()) {
  const root = path.join(home, ".agents/plans")
  if (typeof planPath !== "string" || !path.isAbsolute(planPath) || /[\x00-\x1f\x7f]/.test(planPath)) throw new Error("Expected an absolute plan path")
  // Command templates expand $ARGUMENTS before processing !`shell` and @files.
  // Keep the path literal, not executable template syntax (spaces are fine).
  if (!/^[A-Za-z0-9_./ -]+$/.test(planPath)) throw new Error("Plan path must use plain ASCII letters, digits, spaces, dots, underscores, slashes and hyphens")
  const relative = path.relative(root, planPath).split(path.sep)
  if (relative.length !== 3 || relative.some((part) => !part || part === "..") || relative[2] !== "plan.md") {
    throw new Error("Use ~/.agents/plans/<project>/<task>/plan.md")
  }
  if (realpathSync(planPath) !== planPath) throw new Error("Symlinked plan paths are not supported")
  const progressPath = path.join(path.dirname(planPath), "progress.md")
  const bytes = readRegular(planPath)
  if (!bytes.length) throw new Error("Plan is empty")
  const progress = readRegular(progressPath, true)
  return { planPath, planHash: hash(bytes), progressPath, progressHash: progress === undefined ? null : hash(progress) }
}

export function unchanged(expected, home) {
  const current = snapshot(expected.planPath, home)
  if (current.planHash !== expected.planHash || current.progressHash !== expected.progressHash) {
    throw new Error("Plan or progress changed; prepare the revised plan for approval again")
  }
  return current
}

export function recordApproval(staged, home) {
  unchanged(staged, home)
  const previous = readRegular(staged.progressPath, true) ?? Buffer.alloc(0)
  if (staged.progressHash !== null && hash(previous) !== staged.progressHash) throw new Error("Progress changed before approval recording")
  const record = {
    event: "user-approved-plan-and-fresh-implementation",
    via: "OpenCode local TUI DialogConfirm onConfirm",
    time: new Date().toISOString(),
    handoffID: staged.id,
    sourceSessionID: staged.sourceSessionID,
    sourceMessageID: staged.sourceMessageID,
    directory: staged.directory,
    planPath: staged.planPath,
    sha256: staged.planHash,
    effects: staged.effects,
    execution: "Native home prompt /implement-plan; build agent; current native model and permission mode; no transcript copy",
    status: "Authorizes one native submission attempt; not evidence that submission or implementation succeeded",
  }
  const addition = `\n\n## Fresh Session Approval\n\n\`\`\`json\n${JSON.stringify(record, null, 2)}\n\`\`\`\n`
  const flags = constants.O_WRONLY | constants.O_NOFOLLOW | (staged.progressHash === null ? constants.O_CREAT | constants.O_EXCL : constants.O_APPEND)
  const fd = openSync(staged.progressPath, flags, 0o600)
  try {
    const stat = fstatSync(fd)
    if (!stat.isFile() || stat.nlink !== 1) throw new Error("Unsafe progress file")
    appendFileSync(fd, addition)
  } finally {
    closeSync(fd)
  }
  // Do not adopt freshly-read plan bytes as the approved baseline if another
  // process edits the plan while the approval record is being appended.
  return unchanged({ ...staged, progressHash: hash(Buffer.concat([previous, Buffer.from(addition)])) }, home)
}
