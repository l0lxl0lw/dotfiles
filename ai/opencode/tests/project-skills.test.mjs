import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import plugin from "../runtime/project-skills.js";

test("project execution overrides native races but preserves explicit commands", async () => {
  const root = await mkdtemp(join(tmpdir(), "project skill "));
  const before = process.env.OPENCODE_SKILL_CATALOG;
  try {
    await mkdir(join(root, "scripts"));
    const file = join(root, "SKILL.md");
    await writeFile(file, "---\nname: example\ndescription: project\n---\nPROJECT CONTENT [$ARGUMENTS]");
    process.env.OPENCODE_SKILL_CATALOG = JSON.stringify({ projects: { example: file } });
    let source = "skill";
    const hooks = await plugin({ client: { command: { list: async () => ({ data: [{ name: "example", source }] }) } } });
    const loaded = { output: "WRONG GLOBAL CONTENT", metadata: { name: "example" } };
    await hooks["tool.execute.after"]({ tool: "skill", args: { name: "example" } }, loaded);
    assert.match(loaded.output, /PROJECT CONTENT/);
    assert.doesNotMatch(loaded.output, /WRONG GLOBAL/);
    assert.equal(loaded.metadata.dir, root);
    const denied = { output: "Permission denied", metadata: {} };
    await hooks["tool.execute.after"]({ tool: "skill", args: { name: "example" } }, denied);
    assert.equal(denied.output, "Permission denied");
    const mismatch = { output: "OTHER SKILL", metadata: { name: "other" } };
    await hooks["tool.execute.after"]({ tool: "skill", args: { name: "example" } }, mismatch);
    assert.deepEqual(mismatch, { output: "OTHER SKILL", metadata: { name: "other" } });
    const command = { parts: [{ id: "1", type: "text", text: "WRONG GLOBAL" }, { type: "file", url: "keep" }] };
    await hooks["command.execute.before"]({ command: "example", arguments: "my arguments" }, command);
    assert.match(command.parts[0].text, /PROJECT CONTENT/);
    assert.match(command.parts[0].text, /my arguments/);
    assert.equal(command.parts[0].id, "1");
    assert.equal(command.parts[1].url, "keep");
    for (const arguments_ of ["", "  spaced arguments  "]) {
      const output = { parts: [{ type: "text", text: "old" }, { type: "text", text: "duplicate" }] };
      await hooks["command.execute.before"]({ command: "example", arguments: arguments_ }, output);
      assert.equal(output.parts.length, 1);
      assert.equal(output.parts[0].text, `PROJECT CONTENT [${arguments_}]\n\nBase directory for this skill: ${root}\n\nUser arguments:\n${arguments_}`);
    }
    await assert.rejects(hooks["command.execute.before"]({ command: "example", arguments: "" }, { parts: [] }), /no text part/);
    source = "command";
    command.parts[0].text = "CUSTOM COMMAND";
    await hooks["command.execute.before"]({ command: "example", arguments: "" }, command);
    assert.equal(command.parts[0].text, "CUSTOM COMMAND");
    // Collision does not change the successful skill-tool path or its base directory.
    const colliding = { output: "GLOBAL", metadata: { name: "example" } };
    await hooks["tool.execute.after"]({ tool: "skill", args: { name: "example" } }, colliding);
    assert.match(colliding.output, /PROJECT CONTENT/);
    assert.equal(colliding.metadata.dir, root);
    source = "mcp";
    await hooks["command.execute.before"]({ command: "example", arguments: "" }, command);
    assert.equal(command.parts[0].text, "CUSTOM COMMAND");
    const failed = await plugin({ client: { command: { list: async () => ({ error: "offline" }) } } });
    await assert.rejects(failed["command.execute.before"]({ command: "example", arguments: "" }, command), /Cannot resolve/);
    const system = { system: [] };
    await hooks["experimental.chat.system.transform"]({}, system);
    assert.match(system.system[0], /Project skill definitions take precedence/);
  } finally {
    if (before === undefined) delete process.env.OPENCODE_SKILL_CATALOG;
    else process.env.OPENCODE_SKILL_CATALOG = before;
    await rm(root, { recursive: true });
  }
});
