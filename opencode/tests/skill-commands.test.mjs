import assert from "node:assert/strict";
import test from "node:test";
import plugin from "../tui/skill-commands.js";

function host(data) {
  const layers = [];
  const inserted = [];
  const controller = new AbortController();
  let cleared = 0;
  const api = {
    client: {
      command: { list: async () => ({ data }) },
      tui: { appendPrompt: async (prompt) => inserted.push(prompt) },
    },
    keymap: {
      getCommands: () => [{ slashName: "help", slashAliases: ["h"] }],
      registerLayer: (layer) => layers.push(layer),
    },
    lifecycle: { signal: controller.signal },
    ui: { dialog: { clear: () => cleared++ } },
  };
  return { api, layers, inserted, controller, cleared: () => cleared };
}

test("exposes global and project skill commands, preserving custom and built-in names", async () => {
  const fixture = host([
    { name: "make-resume", source: "skill", description: "Tailor a resume" },
    { name: "global-skill", source: "skill" },
    { name: "custom", source: "command", template: "Keep this workflow" },
    { name: "custom", source: "skill" },
    { name: "remote", source: "mcp" },
    { name: "help", source: "skill" },
    { name: "h", source: "skill" },
  ]);
  await plugin.tui(fixture.api);
  const commands = fixture.layers[0].commands;
  assert.deepEqual(commands.map((command) => command.slashName), ["make-resume", "global-skill"]);
  assert.equal(commands[0].namespace, "palette");
  assert.equal(commands[0].desc, "Tailor a resume");
  await commands[0].run();
  assert.deepEqual(fixture.inserted, [{ text: "/make-resume " }]);
  assert.equal(fixture.cleared(), 1);
});

test("hides workflow snapshot aliases while retaining ordinary workflow skills", async () => {
  const fixture = host([
    { name: "wf-345045be3b-git-commit", source: "skill" },
    { name: "wf-ec476e75e8-poke-holes", source: "skill" },
    { name: "git-commit", source: "skill" },
    { name: "workflow-execute", source: "skill" },
    { name: "wf-helper", source: "skill" },
  ]);
  await plugin.tui(fixture.api);
  assert.deepEqual(fixture.layers[0].commands.map((command) => command.slashName), [
    "git-commit", "workflow-execute", "wf-helper",
  ]);
});

test("a TUI built-in collision selects an executable server fallback", async () => {
  const fixture = host([
    { name: "help", source: "skill", description: "A project help skill" },
    { name: "skill-help", source: "command", description: "Skill fallback: help", template: "Read skill file" },
  ]);
  await plugin.tui(fixture.api);
  const command = fixture.layers[0].commands[0];
  assert.equal(command.slashName, "skill-help");
  await command.run();
  assert.deepEqual(fixture.inserted, [{ text: "/skill-help " }]);
});

test("does not register after disposal or silently accept a failed catalog request", async () => {
  const fixture = host([{ name: "sample", source: "skill" }]);
  fixture.controller.abort();
  await plugin.tui(fixture.api);
  assert.equal(fixture.layers.length, 0);
  await assert.rejects(plugin.tui(host(undefined).api), /Unable to load/);
});
