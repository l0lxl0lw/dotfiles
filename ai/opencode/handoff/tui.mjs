import { createHandoff } from "./native.mjs"
import { listenLocal } from "./transport.mjs"

export default {
  id: "dotfiles.fresh-session-handoff",
  async tui(api) {
    if (api.app.version !== "1.18.30") throw new Error("Fresh handoff is verified only for OpenCode 1.18.30; review the native prompt path before enabling on another version")
    const handoff = createHandoff(api)
    api.lifecycle.onDispose(() => handoff.dispose())
    api.slots.register({
      slots: {
        home_prompt(_context, value) {
          return api.ui.Prompt({
            ref(ref) {
              // Home.bind can seed/auto-submit the original CLI --prompt on
              // its first mount. This arrival belongs ONLY to the approval.
              if (!handoff.bindHome(ref)) value.ref?.(ref)
            },
            right: api.ui.Slot({ name: "home_prompt_right" }),
            placeholders: { normal: ["Fix a TODO in the codebase", "What is the tech stack of this project?", "Fix broken tests"], shell: ["ls -la", "git status", "pwd"] },
          })
        },
        session_prompt(_context, value) {
          return api.ui.Prompt({
            get sessionID() { return value.session_id },
            get visible() { return value.visible },
            get disabled() { return value.disabled },
            onSubmit() { value.on_submit?.() },
            ref(ref) { handoff.bindSource(ref); value.ref?.(ref) },
            right: api.ui.Slot({ name: "session_prompt_right", get session_id() { return value.session_id } }),
          })
        },
      },
    })
    api.event.on("message.part.updated", handoff.part)
    const close = await listenLocal(handoff.handle)
    api.lifecycle.onDispose(close)
    const timer = setInterval(() => { void handoff.tick() }, 100)
    api.lifecycle.onDispose(() => clearInterval(timer))
  },
}
