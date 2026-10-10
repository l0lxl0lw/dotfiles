import assert from "node:assert/strict";
import test from "node:test";
import plugin from "../runtime/delivery-context.js";

test("delivery identity is the current host session, including fresh workers", async () => {
  const hooks = await plugin();
  for (const sessionID of ["ses_owner", "ses_writer", "ses_reviewer"]) {
    const output = { system: [] };
    await hooks["experimental.chat.system.transform"]({ sessionID }, output);
    assert.equal(output.system.length, 1);
    assert.ok(output.system[0].includes(JSON.stringify(sessionID)));
    assert.ok(output.system[0].includes("does not authorize"));
  }
  const output = { system: [] };
  await hooks["experimental.chat.system.transform"]({}, output);
  assert.deepEqual(output.system, []);
});
