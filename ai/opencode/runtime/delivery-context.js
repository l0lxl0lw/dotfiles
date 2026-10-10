// Supply the host's real session identity to delivery owners and fresh workers.
// This does not grant authority or acknowledge a run on their behalf.
export default async () => ({
  "experimental.chat.system.transform": async (input, output) => {
    if (!input.sessionID) return;
    output.system.push(
      `Workflow session ID: ${JSON.stringify(input.sessionID)}. ` +
      "Use this actual host identity for delivery.py ack/claim when a delivery run requests it. " +
      "Its presence does not authorize a delivery or any Git operation.",
    );
  },
});
