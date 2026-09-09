import { homedir } from "node:os"
import path from "node:path"
import { snapshot } from "../handoff/common.mjs"
import { prepareLocal } from "../handoff/transport.mjs"

export default async () => {
  // Resolve from the installed global package, not this symlink's dotfiles realpath.
  const config = path.join(process.env.XDG_CONFIG_HOME || path.join(homedir(), ".config"), "opencode")
  const { tool } = await import(Bun.resolveSync("@opencode-ai/plugin", config))
  return {
    tool: {
      prepare_plan_handoff: tool({
        description: "Stage a completed plan for ONE local TUI popup approving its exact bytes and starting implement-plan in a fresh session. Does not approve or start work. On success STOP your turn; the popup waits for source idle. On failure use normal manual approval and handoff.",
        args: {
          planPath: tool.schema.string().describe("Absolute ~/.agents/plans/<project>/<task>/plan.md path"),
          effects: tool.schema.string().min(1).max(4000).describe("Material effects, verification budget, targets, exclusions and blockers the popup must disclose"),
        },
        async execute(args, context) {
          const staged = snapshot(args.planPath)
          const result = await prepareLocal({
            ...staged,
            effects: args.effects,
            sourceSessionID: context.sessionID,
            sourceMessageID: context.messageID,
            directory: context.directory,
          }, context.abort)
          context.metadata({ metadata: { handoffID: result.id } })
          return `Prepared handoff ${result.id}. No approval yet. STOP now, without more tools or approval questions. The local TUI will ask after this source is idle. Cancellation starts nothing. Do not retry automatically.`
        },
      }),
    },
  }
}
