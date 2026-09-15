// OpenCode already executes skill commands; its slash menu hides source=skill.
// Expose the resolved catalog rather than rescanning files or copying prompts.
export default {
  id: "dotfiles.skill-commands",
  async tui(api) {
    const { data, error } = await api.client.command.list();
    if (error || !Array.isArray(data)) {
      throw new Error("Unable to load the OpenCode skill command catalog");
    }
    if (api.lifecycle.signal.aborted) return;

    const reserved = new Set(
      api.keymap.getCommands().flatMap((command) => [
        command.slashName,
        ...(command.slashAliases ?? []),
      ]),
    );
    for (const command of data) {
      if (command.source !== "skill") reserved.add(command.name);
    }

    api.keymap.registerLayer({
      commands: data
        .filter((command) =>
          command.source === "skill" &&
          !reserved.has(command.name) &&
          !/^wf-[a-f0-9]+-/i.test(command.name)
        )
        .map((command) => ({
          namespace: "palette",
          name: `dotfiles.skill.${command.name}`,
          title: command.name,
          desc: command.description,
          category: "Skills",
          slashName: command.name,
          async run() {
            api.ui.dialog.clear();
            await api.client.tui.appendPrompt({ text: `/${command.name} ` });
          },
        })),
    });
  },
};
