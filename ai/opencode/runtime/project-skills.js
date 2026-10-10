import { readFile } from "node:fs/promises";
import { dirname } from "node:path";

// Native discovery can load duplicate names concurrently. Enforce the launcher's
// project winner after native permission checks and before command execution.
export default async ({ client }) => {
  const { projects = {} } = JSON.parse(process.env.OPENCODE_SKILL_CATALOG || "{}");
  const read = async (name) => {
    const location = projects[name];
    const text = await readFile(location, "utf8");
    const content = text.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, "");
    return { location, content, base: dirname(location) };
  };
  return {
    "tool.execute.after": async (input, output) => {
      if (input.tool !== "skill" || !projects[input.args.name] || output.metadata?.name !== input.args.name) return;
      const name = input.args.name;
      const skill = await read(name);
      output.title = `Loaded skill: ${name}`;
      output.output = `<skill_content name="${name}">\n${skill.content}\n\nBase directory for this skill: ${skill.base}\nRelative paths resolve from this directory.\n</skill_content>`;
      output.metadata = { ...output.metadata, name, dir: skill.base };
    },
    "command.execute.before": async (input, output) => {
      if (!projects[input.command]) return;
      const { data, error } = await client.command.list();
      if (error || !Array.isArray(data)) throw new Error("Cannot resolve project skill command");
      // Explicit commands retain their routing and content; the skill tool remains
      // available for a project skill with that same name, subject to permissions.
      if (data.find((item) => item.name === input.command)?.source !== "skill") return;
      const skill = await read(input.command);
      const text = `${skill.content.replaceAll("$ARGUMENTS", input.arguments)}\n\nBase directory for this skill: ${skill.base}\n\nUser arguments:\n${input.arguments}`;
      const first = output.parts.findIndex((part) => part.type === "text");
      if (first < 0) throw new Error("Project skill command has no text part");
      output.parts = output.parts.filter((part, index) => part.type !== "text" || index === first)
        .map((part) => part.type === "text" ? { ...part, text } : part);
    },
    "experimental.chat.system.transform": async (_input, output) => {
      if (!Object.keys(projects).length) return;
      output.system.push("Project skill definitions take precedence over same-name global definitions. " +
        "The skill tool and native skill commands load these exact files:\n" +
        Object.entries(projects).map(([name, file]) => `${name}: ${file}`).join("\n"));
    },
  };
};
